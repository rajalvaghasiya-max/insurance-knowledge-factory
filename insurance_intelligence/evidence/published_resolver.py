"""Publication-backed Evidence Resolver for ordinary user-answer use.

This path is intentionally separate from the historical MO-016 raw-binding pilot.
It resolves product identity through the existing registry adapter, obtains a bounded
published-evidence source from an injected adapter, and materializes only evidence IDs
that crossed the authoritative-publication gate.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
from typing import Callable

from insurance_intelligence.contracts.evidence import (
    DocumentResolution,
    EntityResolution,
    EvidenceResolverInput,
    EvidenceResolverOutput,
    RequirementResult,
    validate_output,
)
from insurance_intelligence.evidence.admission import USER_ANSWER, evidence_use_from_context
from insurance_intelligence.evidence.published_materialization import (
    PublishedEvidenceMaterializationError,
    PublishedEvidenceSource,
    materialize_published_requirement,
)
from insurance_intelligence.evidence.repositories import RegistryBackedRepository
from insurance_intelligence.evidence.sufficiency import evaluate
from insurance_intelligence.evidence.trace import TraceBuilder

PublishedSourceLookup = Callable[[str, object], PublishedEvidenceSource | None]


def _id(prefix: str, *parts: object) -> str:
    return prefix + "_" + hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


def _resolved_mapping(context: object, key: str) -> dict[str, str]:
    if not isinstance(context, dict):
        return {}
    raw = context.get(key, {})
    if not isinstance(raw, dict):
        return {}
    return {
        str(name): str(value)
        for name, value in raw.items()
        if isinstance(name, str)
        and name.strip()
        and isinstance(value, str)
        and value.strip()
    }


def _semantic_subject(requirement, context: object) -> str:
    resolved_context = _resolved_mapping(context, "resolved_context_values")
    return resolved_context.get(requirement.subject_reference, requirement.subject_reference)


def _instance_candidate(requirement, context: object, semantic_subject: str) -> str:
    """Return the only governed instance candidate available for this requirement.

    Planner subject references may name semantic slots (for example ``term_or_concept``)
    rather than product identities.  Exact candidate substitutions remain preferred.  If
    the subject is semantic, one unique already-resolved candidate identity may be reused;
    zero or multiple identities deliberately do not guess.  Direct canonical subjects keep
    the historical resolver behaviour by falling back to the semantic subject itself.
    """
    candidates = _resolved_mapping(context, "resolved_candidate_references")
    exact = candidates.get(requirement.subject_reference)
    if exact is not None:
        return exact
    unique = tuple(sorted(set(candidates.values())))
    if len(unique) == 1:
        return unique[0]
    if not unique:
        return semantic_subject
    return ""


def _lookup_requirement(requirement, *, semantic_subject: str, plan_goal: str):
    """Project resolved request semantics into the existing topic-neutral source lookup.

    The planner's evidence requirement and plan goal are both governed planner output.  A
    symbolic subject alone (``term_or_concept``) may not contain enough text to select one
    publication artifact, while the plan goal retains the user's bounded requested outcome.
    This projection changes neither evidence category nor authority/version requirements.
    """
    return replace(
        requirement,
        subject_reference=semantic_subject,
        reason=f"{requirement.reason} {plan_goal}".strip(),
    )


class PublishedEvidenceResolver:
    """Resolve only authoritative-publication-backed evidence for USER_ANSWER."""

    def __init__(self, source_lookup: PublishedSourceLookup) -> None:
        if not callable(source_lookup):
            raise TypeError("source_lookup must be callable")
        self._source_lookup = source_lookup

    def resolve(self, request: EvidenceResolverInput) -> EvidenceResolverOutput:
        evidence_use = evidence_use_from_context(request.resolution_context)
        if evidence_use != USER_ANSWER:
            raise ValueError("PublishedEvidenceResolver requires evidence_use=USER_ANSWER")

        plan = request.reasoning_plan
        rid = _id("published_res", request.request_id, plan.plan_id, request.strict_mode)
        trace = TraceBuilder(_id("trace", rid))
        if plan.plan_status == "OUT_OF_SCOPE" or plan.execution_mode == "NO_EXECUTION":
            status = "OUT_OF_SCOPE" if plan.plan_status == "OUT_OF_SCOPE" else "NO_REQUIREMENTS"
            trace.add("RESOLUTION_COMPLETED", status, "plan does not authorize evidence execution")
            return validate_output(EvidenceResolverOutput(
                "1.0", request.request_id, rid, (), (), (), (), (), (), "MISSING", (), trace.build(), status, 1.0
            ))
        if not plan.required_evidence:
            trace.add("RESOLUTION_COMPLETED", "NO_REQUIREMENTS", "plan declares no evidence requirements")
            return validate_output(EvidenceResolverOutput(
                "1.0", request.request_id, rid, (), (), (), (), (), (), "MISSING", (), trace.build(), "NO_REQUIREMENTS", 1.0
            ))

        repo = RegistryBackedRepository(request.repository_roots[0])
        packages = []
        results = []
        entities = []
        documents = []
        missing = []
        limitations = []

        for requirement in plan.required_evidence:
            semantic_subject = _semantic_subject(requirement, request.resolution_context)
            instance_candidate = _instance_candidate(
                requirement,
                request.resolution_context,
                semantic_subject,
            )
            trace.add(
                "REQUIREMENT_RECEIVED", "accepted", "planner evidence requirement received",
                requirement_id=requirement.requirement_id,
                subject_reference=semantic_subject,
            )
            entity, alias = repo.resolve_entity(instance_candidate) if instance_candidate else (None, None)
            if not entity:
                entities.append(EntityResolution(
                    instance_candidate or semantic_subject,
                    None,
                    "NOT_FOUND",
                    "no single governed instance identity matched",
                    None,
                    0.0,
                    (),
                    (),
                ))
                missing.append(requirement.requirement_id)
                results.append(RequirementResult(
                    requirement.requirement_id,
                    "ENTITY_UNRESOLVED",
                    (),
                    (),
                    "governed entity could not be resolved unambiguously",
                    False,
                    False,
                    False,
                    "NONE",
                    0.0,
                ))
                trace.add(
                    "ENTITY_REJECTED",
                    "not found",
                    "no single governed entity match",
                    requirement_id=requirement.requirement_id,
                    subject_reference=semantic_subject,
                )
                continue

            entities.append(EntityResolution(
                instance_candidate,
                entity,
                "RESOLVED",
                "exact governed alias/identity match",
                alias,
                1.0,
                (),
                (),
            ))
            trace.add(
                "ENTITY_RESOLVED",
                entity,
                "governed alias/identity match",
                requirement_id=requirement.requirement_id,
                subject_reference=semantic_subject,
            )
            lookup_requirement = _lookup_requirement(
                requirement,
                semantic_subject=semantic_subject,
                plan_goal=plan.goal,
            )
            source = self._source_lookup(entity, lookup_requirement)
            if source is None:
                reason = "no authoritative publication-backed evidence source matched the requirement"
                missing.append(requirement.requirement_id)
                limitations.append(f"{requirement.requirement_id}: {reason}")
                results.append(RequirementResult(
                    requirement.requirement_id, "MISSING", (), (), reason,
                    False, False, False, "NONE", 0.0,
                ))
                trace.add(
                    "DOCUMENT_REJECTED", "publication source missing", reason,
                    requirement_id=requirement.requirement_id,
                    subject_reference=semantic_subject,
                )
                continue

            try:
                materialized, requirement_result = materialize_published_requirement(
                    source=source,
                    requirement_id=requirement.requirement_id,
                    subject_reference=semantic_subject,
                )
            except PublishedEvidenceMaterializationError as exc:
                reason = str(exc)
                missing.append(requirement.requirement_id)
                limitations.append(f"{requirement.requirement_id}: {reason}")
                results.append(RequirementResult(
                    requirement.requirement_id, "MISSING", (), (), reason,
                    False, False, False, "NONE", 0.0,
                ))
                trace.add(
                    "DOCUMENT_REJECTED", "publication materialization failed", reason,
                    requirement_id=requirement.requirement_id,
                    subject_reference=semantic_subject,
                )
                continue

            packages.extend(materialized)
            results.append(requirement_result)
            seen_documents: set[tuple[str, str]] = set()
            for package in materialized:
                key = (package.document_reference, package.document_version)
                if key not in seen_documents:
                    seen_documents.add(key)
                    documents.append(DocumentResolution(
                        package.document_reference,
                        package.source_type,
                        entity,
                        package.document_version,
                        package.version_status,
                        package.effective_from,
                        package.effective_to,
                        package.lineage.lineage_status,
                        "authoritative publication admitted certified evidence lineage",
                        "RESOLVED",
                    ))
                trace.add(
                    "EVIDENCE_PACKAGED", package.evidence_id,
                    "certified evidence admitted through authoritative publication",
                    requirement_id=requirement.requirement_id,
                    subject_reference=semantic_subject,
                    source_paths=(source.publication.publication_id, source.publication.publication_receipt_id),
                )

        sufficiency, status = evaluate(results)
        confidence = round(sum(item.confidence for item in results) / len(results), 4) if results else 1.0
        trace.add("SUFFICIENCY_EVALUATED", sufficiency, "deterministic requirement-level aggregation")
        trace.add("RESOLUTION_COMPLETED", status, "resolution status derived from publication-backed evidence sufficiency")
        return validate_output(EvidenceResolverOutput(
            "1.0",
            request.request_id,
            rid,
            tuple(packages),
            tuple(results),
            tuple(entities),
            tuple(documents),
            (),
            tuple(missing),
            sufficiency,
            tuple(limitations),
            trace.build(),
            status,
            confidence,
        ))


__all__ = ["PublishedEvidenceResolver", "PublishedSourceLookup"]
