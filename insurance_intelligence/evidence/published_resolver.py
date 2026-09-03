"""Publication-backed Evidence Resolver for ordinary user-answer use.

This path is intentionally separate from the historical MO-016 raw-binding pilot.
It resolves product identity through the existing registry adapter, obtains a bounded
published-evidence source from an injected adapter, and materializes only evidence IDs
that crossed the authoritative-publication gate.
"""
from __future__ import annotations

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


def _subject(requirement, context):
    direct = context.get("resolved_candidate_references", {}) if isinstance(context, dict) else {}
    return str(direct.get(requirement.subject_reference, requirement.subject_reference))


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
            subject = _subject(requirement, request.resolution_context)
            trace.add(
                "REQUIREMENT_RECEIVED", "accepted", "planner evidence requirement received",
                requirement_id=requirement.requirement_id, subject_reference=subject,
            )
            entity, alias = repo.resolve_entity(subject)
            if not entity:
                entities.append(EntityResolution(
                    subject, None, "NOT_FOUND", "no governed alias or identity matched", None, 0.0, (), ()
                ))
                missing.append(requirement.requirement_id)
                results.append(RequirementResult(
                    requirement.requirement_id, "ENTITY_UNRESOLVED", (), (),
                    "governed entity could not be resolved", False, False, False, "NONE", 0.0,
                ))
                trace.add(
                    "ENTITY_REJECTED", "not found", "no governed entity match",
                    requirement_id=requirement.requirement_id, subject_reference=subject,
                )
                continue

            entities.append(EntityResolution(
                subject, entity, "RESOLVED", "exact governed alias/identity match", alias, 1.0, (), ()
            ))
            trace.add(
                "ENTITY_RESOLVED", entity, "governed alias/identity match",
                requirement_id=requirement.requirement_id, subject_reference=subject,
            )
            source = self._source_lookup(entity, requirement)
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
                    requirement_id=requirement.requirement_id, subject_reference=subject,
                )
                continue

            try:
                materialized, requirement_result = materialize_published_requirement(
                    source=source,
                    requirement_id=requirement.requirement_id,
                    subject_reference=subject,
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
                    requirement_id=requirement.requirement_id, subject_reference=subject,
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
                    subject_reference=subject,
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
