"""Generic certification of governed waiting-period bindings.

The builder is insurer-independent. It regenerates a reviewed waiting-period binding,
verifies its registered primary-legal lineage, and maps the resolved typed mechanic
into the existing generic waiting-period completeness topic. It does not publish the
mechanic, infer customer-specific eligibility, or resolve unrelated waiting-period
families.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.waiting_period_binding import WaitingPeriodBinding
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


class WaitingPeriodCertificationError(ValueError):
    """Raised when a governed waiting-period binding cannot be certified safely."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodCertificationError(f"{label} must be non-empty text")
    return value.strip()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodCertificationError(f"{label} must be a JSON array")
    return value


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodCertificationError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative_path: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise WaitingPeriodCertificationError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise FileNotFoundError(f"{label} was not found: {relative_path}")
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WaitingPeriodCertificationError(f"{label} must be valid UTF-8 JSON") from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    result: dict[str, Mapping[str, Any]] = {}
    for raw in _items(review.get("candidates"), "registration.evidence_review.candidates"):
        candidate = _mapping(raw, "candidate")
        result[_text(candidate.get("candidate_id"), "candidate.candidate_id")] = candidate
    return result


def _requirement(requirement_id: str, evidence_ids: tuple[str, ...]) -> RequirementResult:
    return RequirementResult(
        requirement_id=requirement_id,
        status="SATISFIED",
        matched_evidence_ids=evidence_ids,
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def _component_evidence(
    *,
    case_id: str,
    component_id: str,
    requirement_type: str,
    claim: str,
    binding_id: str,
    binding_spec_path: str,
    binding_spec_sha: str,
    document: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_role: str,
) -> EvidencePackage:
    requirement_id = f"requirement:{case_id}:{component_id}"
    evidence_id = f"evidence:{case_id}:{component_id}:{candidate_role}"
    document_id = _text(document.get("document_id"), "document.document_id")
    document_version_id = _text(document.get("document_version_id"), "document.document_version_id")
    source_path = _text(document.get("storage_locator"), "document.storage_locator")
    source_sha = _text(document.get("content_sha256"), "document.content_sha256")
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference=f"waiting_period_binding:{binding_id}",
        governed_entity_reference=f"waiting_period_binding:{binding_id}",
        field_or_topic=requirement_type,
        claim=claim,
        evidence_role="DEFINING",
        source_type=_text(document.get("document_type"), "document.document_type").upper(),
        document_reference=document_id,
        document_version=document_version_id,
        effective_from=None,
        effective_to=None,
        page=candidate.get("source_page"),
        section="Waiting period",
        source_excerpt=_text(candidate.get("excerpt"), "candidate.excerpt"),
        normalized_fact_reference=f"{binding_id}:{component_id}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=Lineage(
            source_artifact_path=source_path,
            source_artifact_sha256=source_sha,
            governed_record_path=binding_spec_path,
            governed_record_sha256=binding_spec_sha,
            binding_reference=f"waiting_period_binding:{binding_id}",
            projection_reference=f"waiting_period:{component_id}",
            lineage_status="VERIFIED",
        ),
        retrieval_basis=(
            "reviewed_waiting_period_binding",
            candidate_role,
            _text(candidate.get("candidate_id"), "candidate.candidate_id"),
        ),
        confidence=1.0,
    )


def build_waiting_period_certification_case(
    *,
    binding_spec_path: str | Path,
    repository_root: str | Path,
) -> RuleCertificationCaseFixture:
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"repository_root was not found: {root}")
    relative_spec = _safe_relative(str(binding_spec_path), "binding_spec_path")
    spec, spec_sha = _load(root, relative_spec, "binding_spec")
    if spec.get("binding_type") != "waiting_period_binding_v1":
        raise WaitingPeriodCertificationError("binding spec type is not supported")
    if spec.get("reviewed_by_human") is not True:
        raise WaitingPeriodCertificationError("binding spec must be human reviewed")

    result = WaitingPeriodBinding().bind(
        spec=spec,
        repository_root=root,
        bound_at="1970-01-01T00:00:00+00:00",
    )
    manifest = _mapping(result.manifest, "binding_manifest")
    if manifest.get("binding_status") != "reviewed_waiting_period_bound_not_published":
        raise WaitingPeriodCertificationError("binding is not review-ready")
    if manifest.get("publication_status") != "bound_not_published":
        raise WaitingPeriodCertificationError("binding must remain bound_not_published")

    bundle_path = _safe_relative(manifest.get("generic_source_bundle_path"), "generic_source_bundle_path")
    bundle, _ = _load(root, bundle_path, "generic_source_bundle")
    sources = {
        _text(source.get("document_id"), "source.document_id"): source
        for source in (
            _mapping(raw, "generic_source")
            for raw in _items(bundle.get("sources"), "generic_source_bundle.sources")
        )
    }

    evidence_entries = _items(manifest.get("evidence"), "binding_manifest.evidence")
    if not evidence_entries:
        raise WaitingPeriodCertificationError("binding has no evidence")

    candidates_by_role: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for raw_entry in evidence_entries:
        entry = _mapping(raw_entry, "binding_evidence")
        role = _text(entry.get("role"), "binding_evidence.role")
        document_id = _text(entry.get("document_id"), "binding_evidence.document_id")
        source = sources.get(document_id)
        if source is None or source.get("authority_role") != "primary_legal":
            raise WaitingPeriodCertificationError("binding evidence must remain primary_legal")
        registration_path = _safe_relative(
            source.get("registration_output_path"), "source.registration_output_path"
        )
        registration, _ = _load(root, registration_path, f"registration[{document_id}]")
        document = _mapping(registration.get("document"), "registration.document")
        candidate_id = _text(entry.get("candidate_id"), "binding_evidence.candidate_id")
        candidate = _candidate_index(registration).get(candidate_id)
        if candidate is None:
            raise WaitingPeriodCertificationError(f"candidate missing from registration: {candidate_id}")
        if candidate.get("text_sha256") != entry.get("candidate_text_sha256"):
            raise WaitingPeriodCertificationError(f"candidate text hash mismatch: {candidate_id}")
        candidates_by_role[role] = (document, candidate)

    if "mechanism" not in candidates_by_role:
        raise WaitingPeriodCertificationError("mechanism evidence is required")
    mechanic = _mapping(manifest.get("mechanic"), "binding_manifest.mechanic")
    binding_id = _text(manifest.get("binding_id"), "binding_manifest.binding_id")
    case_id = f"waiting_period:{binding_id}"

    duration_claim = f"The waiting period duration is {mechanic.get('duration_value')} {mechanic.get('duration_unit')}."
    subject_values = tuple(_text(value, "mechanic.applies_to[]") for value in _items(mechanic.get("applies_to"), "mechanic.applies_to"))
    subject_claim = "Waiting period applies to: " + "; ".join(subject_values) + "."
    start_claim = f"The waiting period start basis is {mechanic.get('start_basis')}."
    scope_bits = [f"scope_type={mechanic.get('scope_type')}"]
    if mechanic.get("scope_reference"):
        scope_bits.append(f"scope_reference={mechanic.get('scope_reference')}")
    if mechanic.get("sum_insured_enhancement_effect"):
        scope_bits.append(f"sum_insured_enhancement_effect={mechanic.get('sum_insured_enhancement_effect')}")
    applicability_claim = "Waiting-period applicability: " + "; ".join(scope_bits) + "."

    component_claims: list[tuple[str, str, str, tuple[str, ...]]] = [
        ("waiting_period_duration", "WAITING_PERIOD_DURATION", duration_claim, ("mechanism", "schedule_value_resolution") if "schedule_value_resolution" in candidates_by_role else ("mechanism",)),
        ("waiting_period_subject", "WAITING_PERIOD_SUBJECT", subject_claim, ("mechanism",)),
        ("start_basis", "WAITING_PERIOD_START_BASIS", start_claim, ("mechanism",)),
        ("applicability_scope", "APPLICABILITY_SCOPE", applicability_claim, ("mechanism",)),
    ]
    if mechanic.get("continuity_dependency"):
        component_claims.append((
            "continuity_or_credit_rule",
            "CONTINUITY_OR_CREDIT_RULE",
            _text(mechanic.get("continuity_dependency"), "mechanic.continuity_dependency"),
            ("mechanism",),
        ))
    exceptions = tuple(
        _text(value, "mechanic.exclusions_or_exceptions[]")
        for value in _items(mechanic.get("exclusions_or_exceptions", []), "mechanic.exclusions_or_exceptions")
    )
    if exceptions:
        component_claims.append((
            "exception_condition",
            "EXCEPTION_CONDITION",
            "Waiting-period exceptions: " + "; ".join(exceptions) + ".",
            ("mechanism",),
        ))

    packages: list[EvidencePackage] = []
    requirements: list[RequirementResult] = []
    for component_id, requirement_type, claim, roles in component_claims:
        component_packages = tuple(
            _component_evidence(
                case_id=case_id,
                component_id=component_id,
                requirement_type=requirement_type,
                claim=claim,
                binding_id=binding_id,
                binding_spec_path=relative_spec,
                binding_spec_sha=spec_sha,
                document=candidates_by_role[role][0],
                candidate=candidates_by_role[role][1],
                candidate_role=role,
            )
            for role in roles
        )
        packages.extend(component_packages)
        requirements.append(
            _requirement(
                f"requirement:{case_id}:{component_id}",
                tuple(package.evidence_id for package in component_packages),
            )
        )

    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=f"waiting_period_binding:{binding_id}",
        topic_id="waiting_period",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(
            build_component_certification_expectation(
                component_id=component_id,
                acceptable_statuses=("SATISFIED",),
            )
            for component_id, _, _, _ in component_claims
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
            "The waiting-period binding remains bound_not_published and is used only for internal certification.",
            "Certification applies only to this resolved waiting-period mechanic and does not certify other waiting-period families.",
            "Certification does not determine customer-specific eligibility or claim payment.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=f"Waiting-period certification for governed binding {binding_id}.",
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )


def run_waiting_period_certification_case(
    case: RuleCertificationCaseFixture,
) -> RuleCertificationResult:
    if not isinstance(case, RuleCertificationCaseFixture):
        raise WaitingPeriodCertificationError("case must be a RuleCertificationCaseFixture")
    return run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )


__all__ = [
    "WaitingPeriodCertificationError",
    "build_waiting_period_certification_case",
    "run_waiting_period_certification_case",
]
