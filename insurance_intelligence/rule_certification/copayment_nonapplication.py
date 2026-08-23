"""Certification for governed explicit co-payment non-application rules."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.copayment_nonapplication_binding import (
    CopaymentNonapplicationBinding,
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
from insurance_intelligence.contracts.topic_completeness import (
    build_component_definition,
    build_topic_definition,
)
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.topic_completeness.registry import TopicCompletenessRegistry


class CopaymentNonapplicationCertificationError(ValueError):
    """Raised when a bound non-application rule cannot be certified safely."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CopaymentNonapplicationCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CopaymentNonapplicationCertificationError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CopaymentNonapplicationCertificationError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise CopaymentNonapplicationCertificationError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise CopaymentNonapplicationCertificationError(
            f"{label} must remain under repository_root"
        ) from exc
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CopaymentNonapplicationCertificationError(f"{label} must be valid JSON") from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


def _registry() -> TopicCompletenessRegistry:
    definition = build_topic_definition(
        topic_id="conditional_copayment_nonapplication",
        topic_version="1.0",
        domain="health",
        components=(
            build_component_definition(
                component_id="affected_cost_share",
                requirement_type="AFFECTED_COST_SHARE",
                required=True,
                acceptable_requirement_statuses=("SATISFIED",),
                acceptable_evidence_roles=("DEFINING",),
                minimum_authority="AUTHORITATIVE",
                dependency_component_ids=(),
                reason="Identify the cost-sharing mechanism that is explicitly disabled.",
            ),
            build_component_definition(
                component_id="nonapplication_effect",
                requirement_type="NONAPPLICATION_EFFECT",
                required=True,
                acceptable_requirement_statuses=("SATISFIED",),
                acceptable_evidence_roles=("DEFINING",),
                minimum_authority="AUTHORITATIVE",
                dependency_component_ids=("affected_cost_share",),
                reason="Preserve that the documented mechanism does not apply rather than manufacturing a zero-valued obligation.",
            ),
            build_component_definition(
                component_id="trigger_condition",
                requirement_type="TRIGGER_CONDITION",
                required=True,
                acceptable_requirement_statuses=("SATISFIED",),
                acceptable_evidence_roles=("DEFINING",),
                minimum_authority="AUTHORITATIVE",
                dependency_component_ids=(),
                reason="Preserve the condition under which non-application is effective.",
            ),
            build_component_definition(
                component_id="applicability_scope",
                requirement_type="APPLICABILITY_SCOPE",
                required=True,
                acceptable_requirement_statuses=("SATISFIED",),
                acceptable_evidence_roles=("DEFINING",),
                minimum_authority="AUTHORITATIVE",
                dependency_component_ids=(),
                reason="Preserve the scope of the non-application rule.",
            ),
        ),
    )
    registry = TopicCompletenessRegistry()
    registry.register(definition, active=True)
    return registry


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    return {
        _text(candidate.get("candidate_id"), "candidate.candidate_id"): candidate
        for candidate in (
            _mapping(raw, "candidate")
            for raw in _items(review.get("candidates"), "registration.evidence_review.candidates")
        )
    }


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


def build_copayment_nonapplication_certification_case(
    *,
    binding_spec_path: str | Path,
    repository_root: str | Path,
) -> RuleCertificationCaseFixture:
    root = Path(repository_root).resolve()
    relative_spec = _safe_relative(str(binding_spec_path), "binding_spec_path")
    spec, spec_sha = _load(root, relative_spec, "binding_spec")
    result = CopaymentNonapplicationBinding().bind(spec=spec, repository_root=root)
    manifest = _mapping(result.manifest, "binding_manifest")
    if manifest.get("binding_status") != "reviewed_copayment_nonapplication_bound_not_published":
        raise CopaymentNonapplicationCertificationError("binding is not review-ready")

    rules = _items(manifest.get("rules"), "binding_manifest.rules")
    if len(rules) != 1:
        raise CopaymentNonapplicationCertificationError(
            "certification currently requires exactly one non-application rule"
        )
    rule = _mapping(rules[0], "binding_rule")
    if rule.get("rule_type") != "conditional_copayment_nonapplication_rule":
        raise CopaymentNonapplicationCertificationError("unsupported rule type")
    if rule.get("publication_status") != "bound_not_published":
        raise CopaymentNonapplicationCertificationError("rule must remain bound_not_published")
    semantic = _mapping(rule.get("semantic"), "binding_rule.semantic")
    if semantic.get("affected_cost_share") != "COPAYMENT":
        raise CopaymentNonapplicationCertificationError("affected cost share must be COPAYMENT")
    if semantic.get("effect") != "DOES_NOT_APPLY":
        raise CopaymentNonapplicationCertificationError("effect must be DOES_NOT_APPLY")

    evidence_entries = _items(rule.get("evidence"), "binding_rule.evidence")
    if len(evidence_entries) != 1:
        raise CopaymentNonapplicationCertificationError("one exact evidence selection is required")
    evidence_entry = _mapping(evidence_entries[0], "binding_rule.evidence[0]")
    if evidence_entry.get("authority_role") != "primary_legal":
        raise CopaymentNonapplicationCertificationError("evidence must remain primary_legal")

    bundle_path = _safe_relative(
        manifest.get("generic_source_bundle_path"), "generic_source_bundle_path"
    )
    bundle, _ = _load(root, bundle_path, "generic_source_bundle")
    sources = {
        _text(source.get("document_id"), "source.document_id"): source
        for source in (
            _mapping(raw, "source")
            for raw in _items(bundle.get("sources"), "generic_source_bundle.sources")
        )
    }
    document_id = _text(evidence_entry.get("document_id"), "evidence.document_id")
    source = sources.get(document_id)
    if source is None or source.get("authority_role") != "primary_legal":
        raise CopaymentNonapplicationCertificationError("bound source is not primary_legal")
    registration_path = _safe_relative(
        source.get("registration_output_path"), "source.registration_output_path"
    )
    registration, _ = _load(root, registration_path, f"registration[{document_id}]")
    document = _mapping(registration.get("document"), "registration.document")
    candidate_id = _text(evidence_entry.get("candidate_id"), "evidence.candidate_id")
    candidate = _candidate_index(registration).get(candidate_id)
    if candidate is None or candidate.get("text_sha256") != evidence_entry.get(
        "candidate_text_sha256"
    ):
        raise CopaymentNonapplicationCertificationError("candidate lineage mismatch")

    rule_id = _text(rule.get("rule_id"), "binding_rule.rule_id")
    case_id = f"copayment_nonapplication:{rule_id}"
    components = (
        ("affected_cost_share", "AFFECTED_COST_SHARE", "COPAYMENT"),
        ("nonapplication_effect", "NONAPPLICATION_EFFECT", "DOES_NOT_APPLY"),
        (
            "trigger_condition",
            "TRIGGER_CONDITION",
            _text(semantic.get("trigger_condition"), "semantic.trigger_condition"),
        ),
        (
            "applicability_scope",
            "APPLICABILITY_SCOPE",
            _text(semantic.get("applicability_scope"), "semantic.applicability_scope"),
        ),
    )

    packages: list[EvidencePackage] = []
    requirements: list[RequirementResult] = []
    for component_id, requirement_type, claim in components:
        requirement_id = f"requirement:{case_id}:{component_id}"
        evidence_id = f"evidence:{case_id}:{component_id}:{candidate_id}"
        packages.append(
            EvidencePackage(
                evidence_id=evidence_id,
                requirement_id=requirement_id,
                subject_reference=f"copayment_nonapplication:{rule_id}",
                governed_entity_reference=f"copayment_nonapplication:{rule_id}",
                field_or_topic=requirement_type,
                claim=claim,
                evidence_role="DEFINING",
                source_type=_text(document.get("document_type"), "document.document_type").upper(),
                document_reference=_text(document.get("document_id"), "document.document_id"),
                document_version=_text(
                    document.get("document_version_id"), "document.document_version_id"
                ),
                effective_from=None,
                effective_to=None,
                page=candidate.get("source_page"),
                section="Co-payment non-application",
                source_excerpt=_text(candidate.get("excerpt"), "candidate.excerpt"),
                normalized_fact_reference=f"{rule_id}:{component_id}",
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
                    binding_reference=f"copayment_nonapplication:{rule_id}",
                    projection_reference=f"copayment_nonapplication:{component_id}",
                    lineage_status="VERIFIED",
                ),
                retrieval_basis=(
                    "reviewed_copayment_nonapplication_binding",
                    rule_id,
                    candidate_id,
                ),
                confidence=1.0,
            )
        )
        requirements.append(_requirement(requirement_id, evidence_id))

    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=f"copayment_nonapplication:{rule_id}",
        topic_id="conditional_copayment_nonapplication",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(
            build_component_certification_expectation(
                component_id=component_id,
                acceptable_statuses=("SATISFIED",),
            )
            for component_id, _, _ in components
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
            "Certification proves only the explicit documented co-payment non-application rule.",
            "It does not manufacture a 0% co-payment obligation or prove claim payment.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description=f"Co-payment non-application certification for {rule_id}.",
        domain="health",
        expectation=expectation,
        evidence_output=output,
        expected_outcome="PASS",
    )


def run_copayment_nonapplication_certification_case(
    case: RuleCertificationCaseFixture,
) -> RuleCertificationResult:
    return run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
        registry=_registry(),
    )


__all__ = [
    "CopaymentNonapplicationCertificationError",
    "build_copayment_nonapplication_certification_case",
    "run_copayment_nonapplication_certification_case",
]
