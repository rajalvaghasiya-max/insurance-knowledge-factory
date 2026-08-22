"""Generic certification for unresolved Schedule-selected waiting-period option domains."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.waiting_period_option_domain_binding import (
    WaitingPeriodOptionDomainBinding,
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


class WaitingPeriodOptionDomainCertificationError(ValueError):
    """Raised when an unresolved waiting-period option domain cannot be certified safely."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodOptionDomainCertificationError(f"{label} must be non-empty text")
    return value.strip()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodOptionDomainCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodOptionDomainCertificationError(f"{label} must be a JSON array")
    return value


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodOptionDomainCertificationError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative_path: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise WaitingPeriodOptionDomainCertificationError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise FileNotFoundError(f"{label} was not found: {relative_path}")
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WaitingPeriodOptionDomainCertificationError(f"{label} must be valid UTF-8 JSON") from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    return {
        _text(candidate.get("candidate_id"), "candidate.candidate_id"): candidate
        for candidate in (
            _mapping(raw, "registration.evidence_review.candidates[]")
            for raw in _items(review.get("candidates"), "registration.evidence_review.candidates")
        )
    }


def _registry() -> TopicCompletenessRegistry:
    definition = build_topic_definition(
        topic_id="waiting_period_option_domain",
        topic_version="1.0",
        domain="health",
        components=(
            build_component_definition(component_id="duration_option_domain", requirement_type="WAITING_PERIOD_DURATION_OPTION_DOMAIN", required=True, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=(), reason="Resolve the complete authoritative selectable duration domain."),
            build_component_definition(component_id="waiting_period_subject", requirement_type="WAITING_PERIOD_SUBJECT", required=True, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=(), reason="Resolve the subject to which the selectable waiting period applies."),
            build_component_definition(component_id="selection_basis", requirement_type="WAITING_PERIOD_SELECTION_BASIS", required=True, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=("duration_option_domain",), reason="Resolve that a concrete duration is selected through the Policy Schedule."),
            build_component_definition(component_id="start_basis", requirement_type="WAITING_PERIOD_START_BASIS", required=True, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=(), reason="Resolve the basis from which the waiting period is measured."),
            build_component_definition(component_id="applicability_scope", requirement_type="APPLICABILITY_SCOPE", required=True, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=(), reason="Resolve the policy or benefit scope affected."),
            build_component_definition(component_id="continuity_or_credit_rule", requirement_type="CONTINUITY_OR_CREDIT_RULE", required=False, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=("start_basis",), reason="Resolve continuity or portability credit when present."),
            build_component_definition(component_id="sum_insured_enhancement_effect", requirement_type="SUM_INSURED_ENHANCEMENT_EFFECT", required=False, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=(), reason="Resolve reapplication on an enhanced Sum Insured when present."),
            build_component_definition(component_id="exception_condition", requirement_type="EXCEPTION_CONDITION", required=False, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=("waiting_period_subject",), reason="Resolve any waiting-period exception when present."),
            build_component_definition(component_id="relationship_rule", requirement_type="WAITING_PERIOD_RELATIONSHIP_RULE", required=False, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=("duration_option_domain",), reason="Resolve interaction with another waiting-period family when present."),
            build_component_definition(component_id="post_wait_condition", requirement_type="POST_WAIT_CONDITION", required=False, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=("waiting_period_subject",), reason="Resolve any condition that still applies after waiting-period expiry."),
        ),
    )
    registry = TopicCompletenessRegistry()
    registry.register(definition, active=True)
    return registry


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


def _evidence_package(*, case_id: str, component_id: str, requirement_type: str, claim: str, binding_id: str, spec_path: str, spec_sha: str, document: Mapping[str, Any], candidate: Mapping[str, Any], role: str) -> EvidencePackage:
    requirement_id = f"requirement:{case_id}:{component_id}"
    evidence_id = f"evidence:{case_id}:{component_id}:{role}"
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference=f"waiting_period_option_domain_binding:{binding_id}",
        governed_entity_reference=f"waiting_period_option_domain_binding:{binding_id}",
        field_or_topic=requirement_type,
        claim=claim,
        evidence_role="DEFINING",
        source_type=_text(document.get("document_type"), "document.document_type").upper(),
        document_reference=_text(document.get("document_id"), "document.document_id"),
        document_version=_text(document.get("document_version_id"), "document.document_version_id"),
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
            source_artifact_path=_text(document.get("storage_locator"), "document.storage_locator"),
            source_artifact_sha256=_text(document.get("content_sha256"), "document.content_sha256"),
            governed_record_path=spec_path,
            governed_record_sha256=spec_sha,
            binding_reference=f"waiting_period_option_domain_binding:{binding_id}",
            projection_reference=f"waiting_period_option_domain:{component_id}",
            lineage_status="VERIFIED",
        ),
        retrieval_basis=("reviewed_waiting_period_option_domain_binding", role, _text(candidate.get("candidate_id"), "candidate.candidate_id")),
        confidence=1.0,
    )


def build_waiting_period_option_domain_certification_case(*, binding_spec_path: str | Path, repository_root: str | Path) -> RuleCertificationCaseFixture:
    root = Path(repository_root).resolve()
    relative_spec = _safe_relative(str(binding_spec_path), "binding_spec_path")
    spec, spec_sha = _load(root, relative_spec, "binding_spec")
    if spec.get("binding_type") != "waiting_period_option_domain_binding_v1":
        raise WaitingPeriodOptionDomainCertificationError("binding spec type is not supported")
    result = WaitingPeriodOptionDomainBinding().bind(spec=spec, repository_root=root, bound_at="1970-01-01T00:00:00+00:00")
    manifest = _mapping(result.manifest, "binding_manifest")
    if manifest.get("binding_status") != "reviewed_waiting_period_option_domain_bound_not_published":
        raise WaitingPeriodOptionDomainCertificationError("binding is not review-ready")
    if manifest.get("resolution_status") != "unresolved_schedule_option_domain":
        raise WaitingPeriodOptionDomainCertificationError("option domain must remain unresolved")
    if manifest.get("policy_instance_resolution_status") != "not_resolved_without_schedule_selection":
        raise WaitingPeriodOptionDomainCertificationError("policy-instance resolution guardrail is missing")
    if manifest.get("publication_status") != "bound_not_published":
        raise WaitingPeriodOptionDomainCertificationError("binding must remain unpublished")

    bundle_path = _safe_relative(manifest.get("generic_source_bundle_path"), "generic_source_bundle_path")
    bundle, _ = _load(root, bundle_path, "generic_source_bundle")
    sources = {
        _text(source.get("document_id"), "source.document_id"): source
        for source in (_mapping(raw, "generic_source") for raw in _items(bundle.get("sources"), "generic_source_bundle.sources"))
    }
    candidates_by_role: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for raw_entry in _items(manifest.get("evidence"), "binding_manifest.evidence"):
        entry = _mapping(raw_entry, "binding_evidence")
        role = _text(entry.get("role"), "binding_evidence.role")
        document_id = _text(entry.get("document_id"), "binding_evidence.document_id")
        source = sources.get(document_id)
        if source is None or source.get("authority_role") != "primary_legal":
            raise WaitingPeriodOptionDomainCertificationError("binding evidence must remain primary_legal")
        registration_path = _safe_relative(source.get("registration_output_path"), "source.registration_output_path")
        registration, _ = _load(root, registration_path, f"registration[{document_id}]")
        document = _mapping(registration.get("document"), "registration.document")
        candidate_id = _text(entry.get("candidate_id"), "binding_evidence.candidate_id")
        candidate = _candidate_index(registration).get(candidate_id)
        if candidate is None or candidate.get("text_sha256") != entry.get("candidate_text_sha256"):
            raise WaitingPeriodOptionDomainCertificationError(f"candidate lineage mismatch: {candidate_id}")
        candidates_by_role[role] = (document, candidate)
    if set(candidates_by_role) != {"mechanism", "option_domain"}:
        raise WaitingPeriodOptionDomainCertificationError("mechanism and option_domain evidence are both required")

    domain = _mapping(manifest.get("option_domain"), "binding_manifest.option_domain")
    semantics = _mapping(spec.get("material_mechanic_semantics", {}), "material_mechanic_semantics")
    binding_id = _text(manifest.get("binding_id"), "binding_id")
    case_id = f"waiting_period_option_domain:{binding_id}"
    options = tuple(_mapping(item, "option_domain.options[]") for item in _items(domain.get("options"), "option_domain.options"))
    option_claim = "Available Schedule-selectable waiting-period durations: " + "; ".join(f"{item.get('duration_value')} {item.get('duration_unit')}" for item in options) + ". No duration is selected by this option-domain binding."
    subjects = tuple(_text(value, "option_domain.applies_to[]") for value in _items(domain.get("applies_to"), "option_domain.applies_to"))
    components: list[tuple[str, str, str, tuple[str, ...]]] = [
        ("duration_option_domain", "WAITING_PERIOD_DURATION_OPTION_DOMAIN", option_claim, ("option_domain",)),
        ("waiting_period_subject", "WAITING_PERIOD_SUBJECT", "Waiting period applies to: " + "; ".join(subjects) + ".", ("mechanism",)),
        ("selection_basis", "WAITING_PERIOD_SELECTION_BASIS", _text(domain.get("schedule_dependency"), "option_domain.schedule_dependency"), ("mechanism", "option_domain")),
        ("start_basis", "WAITING_PERIOD_START_BASIS", f"The waiting period start basis is {_text(semantics.get('start_basis'), 'material_mechanic_semantics.start_basis')}.", ("mechanism",)),
        ("applicability_scope", "APPLICABILITY_SCOPE", f"Waiting-period applicability: scope_type={domain.get('scope_type')}.", ("mechanism",)),
    ]
    optional = (
        ("continuity_credit", "continuity_or_credit_rule", "CONTINUITY_OR_CREDIT_RULE"),
        ("sum_insured_enhancement_effect", "sum_insured_enhancement_effect", "SUM_INSURED_ENHANCEMENT_EFFECT"),
        ("post_wait_condition", "post_wait_condition", "POST_WAIT_CONDITION"),
        ("longer_of_relationship", "relationship_rule", "WAITING_PERIOD_RELATIONSHIP_RULE"),
    )
    for source_key, component_id, requirement_type in optional:
        if semantics.get(source_key):
            components.append((component_id, requirement_type, _text(semantics.get(source_key), f"material_mechanic_semantics.{source_key}"), ("mechanism",)))
    if semantics.get("accident_exception") is True:
        components.append(("exception_condition", "EXCEPTION_CONDITION", "This waiting-period exclusion does not apply to claims arising due to an Accident.", ("mechanism",)))

    packages: list[EvidencePackage] = []
    requirements: list[RequirementResult] = []
    for component_id, requirement_type, claim, roles in components:
        component_packages = tuple(
            _evidence_package(case_id=case_id, component_id=component_id, requirement_type=requirement_type, claim=claim, binding_id=binding_id, spec_path=relative_spec, spec_sha=spec_sha, document=candidates_by_role[role][0], candidate=candidates_by_role[role][1], role=role)
            for role in roles
        )
        packages.extend(component_packages)
        requirements.append(_requirement(f"requirement:{case_id}:{component_id}", tuple(item.evidence_id for item in component_packages)))

    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=f"waiting_period_option_domain_binding:{binding_id}",
        topic_id="waiting_period_option_domain",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(build_component_certification_expectation(component_id=component_id, acceptable_statuses=("SATISFIED",)) for component_id, _, _, _ in components),
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
            "Certification proves an authoritative unresolved waiting-period option domain, not a selected duration.",
            "A customer-specific duration remains unresolved until authoritative Policy Schedule evidence supplies the selection.",
            "The option-domain binding remains bound_not_published and does not authorize publication, comparison readiness, decision support, eligibility, or claim payment.",
        ),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    return RuleCertificationCaseFixture(case_id=case_id, description=f"Waiting-period option-domain certification for {binding_id}.", domain="health", expectation=expectation, evidence_output=output, expected_outcome="PASS")


def run_waiting_period_option_domain_certification_case(case: RuleCertificationCaseFixture) -> RuleCertificationResult:
    if not isinstance(case, RuleCertificationCaseFixture):
        raise WaitingPeriodOptionDomainCertificationError("case must be a RuleCertificationCaseFixture")
    return run_rule_certification(expectation=case.expectation, evidence_output=case.evidence_output, domain=case.domain, registry=_registry())


__all__ = [
    "WaitingPeriodOptionDomainCertificationError",
    "build_waiting_period_option_domain_certification_case",
    "run_waiting_period_option_domain_certification_case",
]
