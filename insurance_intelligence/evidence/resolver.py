"""Deterministic, read-only governed Evidence Resolver."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
)
from insurance_intelligence.contracts.evidence import *
from insurance_intelligence.evidence.admission import (
    USER_ANSWER,
    evaluate_publication_admission,
    evidence_use_from_context,
)
from insurance_intelligence.evidence.authority import (
    authority_rank,
    normalize_source_type,
    satisfies_authority,
)
from insurance_intelligence.evidence.repositories import RegistryBackedRepository
from insurance_intelligence.evidence.sufficiency import evaluate
from insurance_intelligence.evidence.trace import TraceBuilder

PublicationLookup = Callable[[str, str], AuthoritativePublicationRecord | None]


def _id(prefix, *parts):
    return prefix + "_" + hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


def _subject(req, ctx):
    direct = ctx.get("resolved_candidate_references", {}) if isinstance(ctx, dict) else {}
    return str(direct.get(req.subject_reference, req.subject_reference))


def _topic(subject, reason):
    s = (subject + " " + reason).lower()
    return "copay" if ("copay" in s or "co-pay" in s or "copayment" in s) else subject


def _publication_topic(topic: str) -> str:
    """Map legacy resolver topic tokens to governed publication topic IDs."""
    return "conditional_copayment" if topic == "copay" else topic


class EvidenceResolver:
    def __init__(self, publication_lookup: PublicationLookup | None = None) -> None:
        self._publication_lookup = publication_lookup

    def resolve(self, request: EvidenceResolverInput) -> EvidenceResolverOutput:
        plan = request.reasoning_plan
        rid = _id("res", request.request_id, plan.plan_id, request.strict_mode)
        trace = TraceBuilder(_id("trace", rid))
        evidence_use = evidence_use_from_context(request.resolution_context)

        if plan.plan_status == "OUT_OF_SCOPE" or plan.execution_mode == "NO_EXECUTION":
            status = "OUT_OF_SCOPE" if plan.plan_status == "OUT_OF_SCOPE" else "NO_REQUIREMENTS"
            trace.add("RESOLUTION_COMPLETED", status, "plan does not authorize evidence execution")
            return validate_output(
                EvidenceResolverOutput(
                    "1.0",
                    request.request_id,
                    rid,
                    (),
                    (),
                    (),
                    (),
                    (),
                    (),
                    "MISSING",
                    (),
                    trace.build(),
                    status,
                    1.0,
                )
            )
        if not plan.required_evidence:
            trace.add("RESOLUTION_COMPLETED", "NO_REQUIREMENTS", "plan declares no evidence requirements")
            return validate_output(
                EvidenceResolverOutput(
                    "1.0",
                    request.request_id,
                    rid,
                    (),
                    (),
                    (),
                    (),
                    (),
                    (),
                    "MISSING",
                    (),
                    trace.build(),
                    "NO_REQUIREMENTS",
                    1.0,
                )
            )

        repo = RegistryBackedRepository(request.repository_roots[0])
        record = repo.load_pilot()
        packages = []
        results = []
        entities = []
        docs = []
        missing = []
        limitations = []

        for req in plan.required_evidence:
            subject = _subject(req, request.resolution_context)
            trace.add(
                "REQUIREMENT_RECEIVED",
                "accepted",
                "planner evidence requirement received",
                requirement_id=req.requirement_id,
                subject_reference=subject,
            )
            trace.add(
                "ENTITY_CANDIDATE_FOUND",
                "candidate",
                "candidate subject sent to governed registry",
                requirement_id=req.requirement_id,
                subject_reference=subject,
                repository=str(repo.root),
                candidate_reference=subject,
            )
            entity, alias = repo.resolve_entity(subject)
            if not entity:
                er = EntityResolution(
                    subject,
                    None,
                    "NOT_FOUND",
                    "no governed alias or identity matched",
                    None,
                    0.0,
                    (),
                    (),
                )
                entities.append(er)
                missing.append(req.requirement_id)
                trace.add(
                    "ENTITY_REJECTED",
                    "not found",
                    "no governed entity match",
                    requirement_id=req.requirement_id,
                    subject_reference=subject,
                )
                results.append(
                    RequirementResult(
                        req.requirement_id,
                        "ENTITY_UNRESOLVED",
                        (),
                        (),
                        "governed entity could not be resolved",
                        False,
                        False,
                        False,
                        "NONE",
                        0.0,
                    )
                )
                continue

            entities.append(
                EntityResolution(
                    subject,
                    entity,
                    "RESOLVED",
                    "exact governed alias/identity match",
                    alias,
                    1.0,
                    (),
                    (),
                )
            )
            trace.add(
                "ENTITY_RESOLVED",
                entity,
                "governed alias/identity match",
                requirement_id=req.requirement_id,
                subject_reference=subject,
                source_paths=(str(record.binding_path),),
            )
            topic = _topic(subject, req.reason)

            if evidence_use == USER_ANSWER:
                publication_topic = _publication_topic(topic)
                publication = (
                    self._publication_lookup(entity, publication_topic)
                    if self._publication_lookup is not None
                    else None
                )
                admission = evaluate_publication_admission(
                    evidence_use=evidence_use,
                    publication=publication,
                    topic_id=publication_topic,
                )
                if not admission.admitted:
                    reason = admission.basis
                    missing.append(req.requirement_id)
                    limitations.append(f"{req.requirement_id}: {reason}")
                    trace.add(
                        "DOCUMENT_REJECTED",
                        "publication admission blocked",
                        reason,
                        requirement_id=req.requirement_id,
                        subject_reference=subject,
                        source_paths=(
                            (admission.publication_id,)
                            if admission.publication_id is not None
                            else ()
                        ),
                    )
                    results.append(
                        RequirementResult(
                            req.requirement_id,
                            "MISSING",
                            (),
                            (),
                            reason,
                            False,
                            False,
                            False,
                            "NONE",
                            0.0,
                        )
                    )
                    continue

            if topic != "copay":
                missing.append(req.requirement_id)
                results.append(
                    RequirementResult(
                        req.requirement_id,
                        "MISSING",
                        (),
                        (),
                        f"bounded v0.1 pilot has no governed evidence for topic {topic}",
                        False,
                        False,
                        False,
                        "NONE",
                        0.0,
                    )
                )
                continue

            source_type = normalize_source_type(record.source_type)
            auth = satisfies_authority(source_type, req.authority_requirement)
            version_ok = req.version_requirement in {"ANY_GOVERNED", "LATEST_AVAILABLE"} or (
                req.version_requirement == "CURRENT_APPLICABLE" and request.as_of_date is None
            )
            lineage_ok = record.binding_sha256 == __import__("json").loads(
                record.projection_path.read_text()
            )["projection_report"]["binding_manifest_sha256"]
            linestatus = "VERIFIED" if lineage_ok else "MISMATCH"
            docs.append(
                DocumentResolution(
                    record.document_id,
                    source_type,
                    entity,
                    record.document_version_id,
                    "CURRENT_GOVERNED",
                    record.effective_from,
                    record.effective_to,
                    linestatus,
                    "canonical projection document linkage",
                    "RESOLVED" if lineage_ok else "FAILED_LINEAGE",
                )
            )
            trace.add(
                "DOCUMENT_SELECTED",
                record.document_id,
                "binding and canonical projection identify the same document",
                requirement_id=req.requirement_id,
                source_paths=(str(record.source_registration_path), str(record.projection_path)),
            )
            trace.add(
                "LINEAGE_VERIFIED" if lineage_ok else "LINEAGE_FAILED",
                linestatus,
                "binding SHA compared to canonical projection lineage manifest",
                requirement_id=req.requirement_id,
                source_paths=(str(record.binding_path), str(record.projection_path)),
            )
            if not lineage_ok and request.strict_mode == "STRICT":
                results.append(
                    RequirementResult(
                        req.requirement_id,
                        "FAILED_LINEAGE",
                        (),
                        (),
                        "binding hash does not match canonical projection lineage",
                        auth,
                        version_ok,
                        False,
                        "NONE",
                        0.0,
                    )
                )
                missing.append(req.requirement_id)
                continue

            eid = _id("ev", req.requirement_id, record.binding_sha256, record.source_text_sha256)
            lineage = Lineage(
                record.source_artifact_path,
                record.source_artifact_sha256,
                str(record.binding_path.relative_to(repo.root.parent.parent.parent)),
                record.binding_sha256,
                str(record.binding_path),
                str(record.projection_path),
                linestatus,
            )
            role = "DEFINING" if source_type == "POLICY_WORDING" else "SUPPORTING"
            confidence = 0.30 + 0.20 + 0.20 + (0.20 if lineage_ok else 0) + (0.10 if auth else 0)
            package = EvidencePackage(
                eid,
                req.requirement_id,
                subject,
                entity,
                topic,
                record.statement,
                role,
                source_type,
                record.document_id,
                record.document_version_id,
                record.effective_from,
                record.effective_to,
                record.page,
                None,
                record.excerpt,
                record.binding_sha256,
                authority_rank(source_type),
                req.authority_requirement,
                "CURRENT_GOVERNED",
                "APPLICABLE",
                lineage,
                (
                    "governed_entity_match",
                    "binding_assertion",
                    "canonical_projection",
                    "source_registration",
                ),
                min(confidence, 1.0),
            )
            packages.append(package)
            trace.add(
                "EVIDENCE_PACKAGED",
                eid,
                "explicit reviewed statement packaged without interpretation",
                requirement_id=req.requirement_id,
                source_paths=(str(record.binding_path),),
            )
            if not auth:
                st = "PARTIALLY_SATISFIED"
                limitations.append(f"{req.requirement_id}: authority requirement not satisfied")
            elif not version_ok:
                st = "VERSION_UNRESOLVED"
                limitations.append(f"{req.requirement_id}: version applicability unresolved")
            elif not lineage_ok:
                st = "SATISFIED_WITH_LIMITATIONS"
                limitations.append(f"{req.requirement_id}: lineage partial in permissive mode")
            else:
                st = "SATISFIED"
            results.append(
                RequirementResult(
                    req.requirement_id,
                    st,
                    (eid,),
                    (),
                    None if st == "SATISFIED" else limitations[-1],
                    auth,
                    version_ok,
                    lineage_ok,
                    "NONE",
                    package.confidence,
                )
            )

        suff, status = evaluate(results)
        conf = round(sum(r.confidence for r in results) / len(results), 4) if results else 1.0
        trace.add("SUFFICIENCY_EVALUATED", suff, "deterministic requirement-level aggregation")
        trace.add("RESOLUTION_COMPLETED", status, "resolution status derived from sufficiency")
        out = EvidenceResolverOutput(
            "1.0",
            request.request_id,
            rid,
            tuple(packages),
            tuple(results),
            tuple(entities),
            tuple(docs),
            (),
            tuple(missing),
            suff,
            tuple(limitations),
            trace.build(),
            status,
            conf,
        )
        return validate_output(out)
