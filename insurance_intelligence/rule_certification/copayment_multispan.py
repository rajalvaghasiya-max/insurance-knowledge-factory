"""Generic component-level certification for multi-span co-payment rate matrices."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.copayment_multispan_binding import CopaymentMultispanBinding
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
from insurance_intelligence.contracts.topic_profile import build_topic_profile
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.topic_completeness.catalogue import (
    build_conditional_obligation_definition,
)


class CopaymentMultispanCertificationError(ValueError):
    """Raised when component-level multispan certification cannot be proven safely."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CopaymentMultispanCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CopaymentMultispanCertificationError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CopaymentMultispanCertificationError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise CopaymentMultispanCertificationError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise CopaymentMultispanCertificationError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise CopaymentMultispanCertificationError(f"{label} not found: {relative}")
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CopaymentMultispanCertificationError(f"{label} must be valid UTF-8 JSON") from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    return {
        _text(candidate.get("candidate_id"), "candidate.candidate_id"): candidate
        for candidate in (
            _mapping(raw, "candidate")
            for raw in _items(review.get("candidates"), "registration.evidence_review.candidates")
        )
    }


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


def _profile():
    definition = build_conditional_obligation_definition()
    return build_topic_profile(
        profile_id="copayment_multispan_component_profile",
        profile_version="1.0",
        definition=definition,
        required_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
            "calculation_basis",
        ),
        optional_component_ids=("exception_condition",),
        explanation_blocking_component_ids=(
            "obligation_value",
            "trigger_condition",
            "applicability_scope",
            "calculation_basis",
        ),
    )


def _format_percentage(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CopaymentMultispanCertificationError("matrix percentage must be numeric")
    numeric = float(value)
    if numeric.is_integer():
        return f"{int(numeric)}%"
    return f"{numeric:g}%"


def _matrix_claim(cells: list[Any]) -> str:
    rows: list[str] = []
    for raw in cells:
        cell = _mapping(raw, "mechanic.cells[]")
        rows.append(
            f"{_text(cell.get('plan_variant'), 'cell.plan_variant')} | "
            f"{_text(cell.get('claimed_category'), 'cell.claimed_category')} = "
            f"{_format_percentage(cell.get('percentage'))}"
        )
    if not rows:
        raise CopaymentMultispanCertificationError("rate matrix must contain at least one cell")
    return (
        "Documented room-category co-payment matrix: "
        + "; ".join(rows)
        + ". One customer-specific percentage is not resolved from the product-level matrix alone."
    )


def build_copayment_multispan_certification_case(
    *,
    binding_spec_path: str | Path,
    repository_root: str | Path,
) -> RuleCertificationCaseFixture:
    root = Path(repository_root).resolve()
    relative_spec = _safe_relative(str(binding_spec_path), "binding_spec_path")
    spec, spec_sha = _load(root, relative_spec, "binding_spec")
    if spec.get("binding_type") != "copayment_multispan_binding_v1":
        raise CopaymentMultispanCertificationError("binding spec is not a copayment multispan contract")
    if spec.get("reviewed_by_human") is not True:
        raise CopaymentMultispanCertificationError("binding spec is not review-ready")

    result = CopaymentMultispanBinding().bind(
        spec=spec,
        repository_root=root,
        bound_at="1970-01-01T00:00:00+00:00",
    )
    manifest = _mapping(result.manifest, "binding_manifest")
    if manifest.get("binding_status") != "reviewed_generic_legal_conditions_bound_not_published":
        raise CopaymentMultispanCertificationError("binding must remain reviewed and unpublished")

    assertions = _items(manifest.get("assertions"), "binding_manifest.assertions")
    if len(assertions) != 1:
        raise CopaymentMultispanCertificationError("exactly one multispan co-payment assertion is required")
    assertion = _mapping(assertions[0], "binding_assertion")
    if assertion.get("publication_status") != "bound_not_published":
        raise CopaymentMultispanCertificationError("assertion must remain bound_not_published")
    assertion_id = _text(assertion.get("assertion_id"), "assertion.assertion_id")

    bundle_path = _safe_relative(
        manifest.get("generic_source_bundle_path"), "generic_source_bundle_path"
    )
    bundle, _ = _load(root, bundle_path, "generic_source_bundle")
    sources = {
        _text(source.get("document_id"), "source.document_id"): source
        for source in (
            _mapping(raw, "source") for raw in _items(bundle.get("sources"), "sources")
        )
    }

    resolved_candidates: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    registrations: dict[str, Mapping[str, Any]] = {}
    indexes: dict[str, dict[str, Mapping[str, Any]]] = {}
    for raw in _items(assertion.get("evidence"), "assertion.evidence"):
        entry = _mapping(raw, "binding_evidence")
        if entry.get("authority_role") != "primary_legal":
            raise CopaymentMultispanCertificationError(
                "all multispan certification evidence must remain primary_legal"
            )
        document_id = _text(entry.get("document_id"), "evidence.document_id")
        source = sources.get(document_id)
        if source is None or source.get("authority_role") != "primary_legal":
            raise CopaymentMultispanCertificationError("bound source is not registered primary_legal")
        if document_id not in registrations:
            registration_path = _safe_relative(
                source.get("registration_output_path"), "registration_output_path"
            )
            registration, _ = _load(root, registration_path, f"registration[{document_id}]")
            registrations[document_id] = registration
            indexes[document_id] = _candidate_index(registration)
        candidate_id = _text(entry.get("candidate_id"), "evidence.candidate_id")
        candidate = indexes[document_id].get(candidate_id)
        if candidate is None or candidate.get("text_sha256") != entry.get("candidate_text_sha256"):
            raise CopaymentMultispanCertificationError(
                f"candidate lineage mismatch: {document_id}:{candidate_id}"
            )
        if candidate_id in resolved_candidates:
            raise CopaymentMultispanCertificationError(f"duplicate candidate ID: {candidate_id}")
        resolved_candidates[candidate_id] = (
            _mapping(registrations[document_id].get("document"), "registration.document"),
            candidate,
        )

    mechanic = _mapping(manifest.get("mechanic"), "mechanic")
    if mechanic.get("instance_resolution_required") is not True:
        raise CopaymentMultispanCertificationError("matrix mechanic must retain instance resolution guard")
    if mechanic.get("unlisted_combination_outcome") != "UNRESOLVED":
        raise CopaymentMultispanCertificationError("unlisted combinations must remain unresolved")

    claims: dict[str, tuple[str, str]] = {
        "obligation_value": (
            "OBLIGATION_VALUE",
            _matrix_claim(_items(mechanic.get("cells"), "mechanic.cells")),
        ),
        "trigger_condition": (
            "TRIGGER_CONDITION",
            _text(mechanic.get("trigger_condition"), "mechanic.trigger_condition"),
        ),
        "applicability_scope": (
            "APPLICABILITY_SCOPE",
            _text(mechanic.get("applicability_scope"), "mechanic.applicability_scope")
            + " Instance-specific resolution dependency: "
            + _text(
                mechanic.get("instance_resolution_dependency"),
                "mechanic.instance_resolution_dependency",
            ),
        ),
        "calculation_basis": (
            "CALCULATION_BASIS",
            "The documented co-payment calculation basis is "
            + _text(mechanic.get("calculation_basis"), "mechanic.calculation_basis")
            + ".",
        ),
    }
    component_map = _mapping(
        manifest.get("component_evidence_candidate_ids"),
        "component_evidence_candidate_ids",
    )
    if set(component_map) != set(claims):
        raise CopaymentMultispanCertificationError(
            "component evidence map must exactly cover the certified components"
        )

    binding_id = _text(manifest.get("binding_id"), "binding_id")
    case_id = f"copayment_multispan:{binding_id}"
    packages: list[EvidencePackage] = []
    requirements: list[RequirementResult] = []
    for component_id, (requirement_type, claim) in claims.items():
        candidate_ids = tuple(
            _text(value, f"{component_id}[]")
            for value in _items(component_map.get(component_id), component_id)
        )
        if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
            raise CopaymentMultispanCertificationError(
                f"component {component_id} must map to unique candidate IDs"
            )
        evidence_ids: list[str] = []
        for candidate_id in candidate_ids:
            resolved = resolved_candidates.get(candidate_id)
            if resolved is None:
                raise CopaymentMultispanCertificationError(
                    f"component {component_id} references unbound candidate {candidate_id}"
                )
            document, candidate = resolved
            evidence_id = f"evidence:{case_id}:{component_id}:{candidate_id}"
            evidence_ids.append(evidence_id)
            role = "CALCULATION_INPUT" if component_id == "calculation_basis" else "DEFINING"
            packages.append(
                EvidencePackage(
                    evidence_id=evidence_id,
                    requirement_id=f"requirement:{case_id}:{component_id}",
                    subject_reference=f"copayment_multispan_binding:{binding_id}",
                    governed_entity_reference=f"assertion:{assertion_id}",
                    field_or_topic=requirement_type,
                    claim=claim,
                    evidence_role=role,
                    source_type=_text(document.get("document_type"), "document.document_type").upper(),
                    document_reference=_text(document.get("document_id"), "document.document_id"),
                    document_version=_text(
                        document.get("document_version_id"), "document.document_version_id"
                    ),
                    effective_from=None,
                    effective_to=None,
                    page=candidate.get("source_page"),
                    section="Room-category co-payment",
                    source_excerpt=_text(candidate.get("excerpt"), "candidate.excerpt"),
                    normalized_fact_reference=f"{binding_id}:{component_id}",
                    authority_rank=1,
                    authority_requirement="AUTHORITATIVE",
                    version_status="CURRENT_APPLICABLE",
                    applicability_status="APPLICABLE",
                    lineage=Lineage(
                        source_artifact_path=_text(
                            document.get("storage_locator"), "document.storage_locator"
                        ),
                        source_artifact_sha256=_text(
                            document.get("content_sha256"), "document.content_sha256"
                        ),
                        governed_record_path=relative_spec,
                        governed_record_sha256=spec_sha,
                        binding_reference=f"copayment_multispan_binding:{binding_id}",
                        projection_reference=f"conditional_obligation:{component_id}",
                        lineage_status="VERIFIED",
                    ),
                    retrieval_basis=(
                        "reviewed_copayment_multispan_binding",
                        "mechanism",
                        component_id,
                        candidate_id,
                    ),
                    confidence=1.0,
                )
            )
        requirements.append(
            _requirement(f"requirement:{case_id}:{component_id}", tuple(evidence_ids))
        )

    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=f"assertion:{assertion_id}",
        topic_id="conditional_obligation",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(
            build_component_certification_expectation(
                component_id=component_id,
                acceptable_statuses=("SATISFIED",),
            )
            for component_id in claims
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
            "Certification preserves exact component-to-candidate attribution across multiple primary-legal spans.",
            "The product-level matrix does not resolve a customer-specific percentage or decide claim payment.",
            "Unlisted plan-variant / claimed-category combinations remain unresolved.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=f"Multi-span co-payment certification for {binding_id}.",
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )


def run_copayment_multispan_certification_case(
    case: RuleCertificationCaseFixture,
) -> RuleCertificationResult:
    return run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
        profile=_profile(),
    )


__all__ = [
    "CopaymentMultispanCertificationError",
    "build_copayment_multispan_certification_case",
    "run_copayment_multispan_certification_case",
]
