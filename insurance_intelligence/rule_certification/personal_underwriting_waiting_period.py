"""Certification for governed personal / underwriting-specific waiting periods."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.personal_underwriting_waiting_period_binding import (
    PersonalUnderwritingWaitingPeriodBinding,
)
from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.contracts.rule_certification import (
    RuleCertificationResult,
    build_component_certification_expectation,
    build_rule_certification_expectation,
)
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture
from insurance_intelligence.rule_certification.runner import run_rule_certification


class PersonalUnderwritingWaitingPeriodCertificationError(ValueError):
    pass


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PersonalUnderwritingWaitingPeriodCertificationError(f"{label} must be a JSON object")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonalUnderwritingWaitingPeriodCertificationError(f"{label} must be non-empty text")
    return value.strip()


def _load(root: Path, relative: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PersonalUnderwritingWaitingPeriodCertificationError(f"{label} must remain under repository_root") from exc
    raw = path.read_bytes()
    try:
        return _mapping(json.loads(raw.decode("utf-8")), label), sha256(raw).hexdigest()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PersonalUnderwritingWaitingPeriodCertificationError(f"{label} must be valid JSON") from exc


def _requirement(requirement_id: str, evidence_id: str) -> RequirementResult:
    return RequirementResult(
        requirement_id=requirement_id,
        status="SATISFIED",
        matched_evidence_ids=(evidence_id,),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def build_personal_underwriting_waiting_period_certification_case(
    *,
    binding_spec_path: str | Path,
    repository_root: str | Path,
) -> RuleCertificationCaseFixture:
    root = Path(repository_root).resolve()
    relative_spec = Path(binding_spec_path).as_posix()
    spec, spec_sha = _load(root, relative_spec, "binding_spec")
    manifest = PersonalUnderwritingWaitingPeriodBinding().bind(
        spec=spec,
        repository_root=root,
        bound_at="1970-01-01T00:00:00+00:00",
    ).manifest
    mechanic = _mapping(manifest.get("mechanic"), "mechanic")
    evidence = _mapping(manifest.get("evidence"), "evidence")
    bundle, _ = _load(root, _text(manifest.get("generic_source_bundle_path"), "generic_source_bundle_path"), "generic_source_bundle")
    source = next(
        (
            _mapping(raw, "source")
            for raw in bundle.get("sources", [])
            if _mapping(raw, "source").get("document_id") == evidence.get("document_id")
        ),
        None,
    )
    if source is None:
        raise PersonalUnderwritingWaitingPeriodCertificationError("bound source is missing")
    registration, _ = _load(root, _text(source.get("registration_output_path"), "registration_output_path"), "source_registration")
    document = _mapping(registration.get("document"), "registration.document")
    candidate = next(
        (
            _mapping(raw, "candidate")
            for raw in _mapping(registration.get("evidence_review"), "evidence_review").get("candidates", [])
            if _mapping(raw, "candidate").get("candidate_id") == evidence.get("candidate_id")
        ),
        None,
    )
    if candidate is None or candidate.get("text_sha256") != evidence.get("candidate_text_sha256"):
        raise PersonalUnderwritingWaitingPeriodCertificationError("candidate lineage mismatch")

    binding_id = _text(manifest.get("binding_id"), "binding_id")
    case_id = f"personal_underwriting_waiting_period:{binding_id}"
    claims = (
        ("maximum_duration", "WAITING_PERIOD_MAXIMUM_DURATION", f"The product wording permits a personal waiting period of up to {mechanic['maximum_duration_value']} {mechanic['maximum_duration_unit']}.") ,
        ("subject_scope", "WAITING_PERIOD_SUBJECT", "The waiting period applies only to underwriting-specified conditions for an individual insured person."),
        ("start_basis", "WAITING_PERIOD_START_BASIS", f"The maximum-bound waiting period uses start basis {mechanic['start_basis']}."),
        ("instance_resolution_dependency", "POLICY_INSTANCE_DEPENDENCY", _text(mechanic.get("instance_resolution_dependency"), "instance_resolution_dependency")),
    )

    packages = []
    requirements = []
    for component_id, requirement_type, claim in claims:
        requirement_id = f"requirement:{case_id}:{component_id}"
        evidence_id = f"evidence:{case_id}:{component_id}"
        package = EvidencePackage(
            evidence_id=evidence_id,
            requirement_id=requirement_id,
            subject_reference=f"waiting_period_binding:{binding_id}",
            governed_entity_reference=f"waiting_period_binding:{binding_id}",
            field_or_topic=requirement_type,
            claim=claim,
            evidence_role="DEFINING",
            source_type=_text(document.get("document_type"), "document.document_type").upper(),
            document_reference=_text(document.get("document_id"), "document.document_id"),
            document_version=_text(document.get("document_version_id"), "document.document_version_id"),
            effective_from=None,
            effective_to=None,
            page=candidate.get("source_page"),
            section="Personal Waiting Period",
            source_excerpt=_text(candidate.get("excerpt"), "candidate.excerpt"),
            normalized_fact_reference=f"{binding_id}:{component_id}",
            authority_rank=1,
            authority_requirement="AUTHORITATIVE",
            version_status="CURRENT_APPLICABLE",
            applicability_status="APPLICABLE",
            lineage=Lineage(
                source_artifact_path=_text(document.get("storage_locator"), "document.storage_locator"),
                source_artifact_sha256=_text(document.get("content_sha256"), "document.content_sha256"),
                governed_record_path=relative_spec,
                governed_record_sha256=spec_sha,
                binding_reference=f"personal_underwriting_waiting_period:{binding_id}",
                projection_reference=f"personal_underwriting_waiting_period:{component_id}",
                lineage_status="VERIFIED",
            ),
            retrieval_basis=("reviewed_personal_underwriting_waiting_period_binding", _text(candidate.get("candidate_id"), "candidate.candidate_id")),
            confidence=1.0,
        )
        packages.append(package)
        requirements.append(_requirement(requirement_id, evidence_id))

    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=f"waiting_period_binding:{binding_id}",
        topic_id="waiting_period",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(
            build_component_certification_expectation(component_id=component_id, acceptable_statuses=("SATISFIED",))
            for component_id, _, _ in claims
        ),
    )
    output = EvidenceResolverOutput(
        contract_version="1.0",
        request_id=f"request:{case_id}",
        resolution_id=f"resolution:{case_id}",
        evidence_packages=tuple(packages),
        requirement_results=tuple(requirements),
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=(),
        sufficiency="COMPLETE",
        limitations=(
            "The certified 48-month value is a maximum product bound, not the insured person's actual waiting period.",
            "Affected conditions and actual duration require policy-instance underwriting evidence.",
            "Certification does not authorize publication, claim prediction, comparison, or recommendation.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=f"Personal underwriting waiting-period certification for {binding_id}.",
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )


def run_personal_underwriting_waiting_period_certification_case(case: RuleCertificationCaseFixture) -> RuleCertificationResult:
    return run_rule_certification(expectation=case.expectation, evidence_output=case.evidence_output, domain=case.domain)


__all__ = [
    "PersonalUnderwritingWaitingPeriodCertificationError",
    "build_personal_underwriting_waiting_period_certification_case",
    "run_personal_underwriting_waiting_period_certification_case",
]
