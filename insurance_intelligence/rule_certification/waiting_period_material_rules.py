"""Certification for generic material rules attached to scalar waiting periods."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.waiting_period_material_rules_binding import WaitingPeriodMaterialRulesBinding
from insurance_intelligence.contracts.evidence import EvidencePackage, EvidenceResolverOutput, Lineage, RequirementResult
from insurance_intelligence.contracts.rule_certification import RuleCertificationResult, build_component_certification_expectation, build_rule_certification_expectation
from insurance_intelligence.contracts.topic_completeness import build_component_definition, build_topic_definition
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.topic_completeness.registry import TopicCompletenessRegistry


class WaitingPeriodMaterialRulesCertificationError(ValueError):
    pass


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodMaterialRulesCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodMaterialRulesCertificationError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodMaterialRulesCertificationError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodMaterialRulesCertificationError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative).resolve()
    path.relative_to(root)
    raw = path.read_bytes()
    return _mapping(json.loads(raw.decode("utf-8")), label), sha256(raw).hexdigest()


def _registry(required_components: tuple[str, ...]) -> TopicCompletenessRegistry:
    allowed = {"relationship_rule", "applicability_condition"}
    if not required_components or not set(required_components).issubset(allowed):
        raise WaitingPeriodMaterialRulesCertificationError("required material-rule components are invalid")
    definition = build_topic_definition(
        topic_id="waiting_period_material_rules",
        topic_version="1.0",
        domain="health",
        components=(
            build_component_definition(component_id="relationship_rule", requirement_type="WAITING_PERIOD_RELATIONSHIP_RULE", required="relationship_rule" in required_components, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=(), reason="Preserve interaction with another waiting-period family."),
            build_component_definition(component_id="applicability_condition", requirement_type="WAITING_PERIOD_APPLICABILITY_CONDITION", required="applicability_condition" in required_components, acceptable_requirement_statuses=("SATISFIED",), acceptable_evidence_roles=("DEFINING",), minimum_authority="AUTHORITATIVE", dependency_component_ids=(), reason="Preserve additional applicability conditions that are not exceptions."),
        ),
    )
    registry = TopicCompletenessRegistry()
    registry.register(definition, active=True)
    return registry


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    return {_text(c.get("candidate_id"), "candidate.candidate_id"): c for c in (_mapping(raw, "candidate") for raw in _items(review.get("candidates"), "registration.evidence_review.candidates"))}


def _requirement(requirement_id: str, evidence_ids: tuple[str, ...]) -> RequirementResult:
    return RequirementResult(requirement_id=requirement_id, status="SATISFIED", matched_evidence_ids=evidence_ids, rejected_candidate_ids=(), missing_reason=None, authority_satisfied=True, version_satisfied=True, lineage_satisfied=True, conflict_status="NONE", confidence=1.0)


def build_waiting_period_material_rules_certification_case(*, binding_spec_path: str | Path, repository_root: str | Path) -> RuleCertificationCaseFixture:
    root = Path(repository_root).resolve()
    relative_spec = _safe_relative(str(binding_spec_path), "binding_spec_path")
    spec, spec_sha = _load(root, relative_spec, "binding_spec")
    result = WaitingPeriodMaterialRulesBinding().bind(spec=spec, repository_root=root, bound_at="1970-01-01T00:00:00+00:00")
    manifest = _mapping(result.manifest, "binding_manifest")
    if manifest.get("material_rules_status") != "reviewed_material_rules_bound_not_published" or manifest.get("publication_status") != "bound_not_published":
        raise WaitingPeriodMaterialRulesCertificationError("material rules binding is not review-ready")

    bundle_path = _safe_relative(manifest.get("generic_source_bundle_path"), "generic_source_bundle_path")
    bundle, _ = _load(root, bundle_path, "generic_source_bundle")
    sources = {_text(s.get("document_id"), "source.document_id"): s for s in (_mapping(raw, "source") for raw in _items(bundle.get("sources"), "generic_source_bundle.sources"))}
    candidate_context: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for raw in _items(manifest.get("evidence"), "binding_manifest.evidence"):
        entry = _mapping(raw, "binding_evidence")
        document_id = _text(entry.get("document_id"), "binding_evidence.document_id")
        source = sources.get(document_id)
        if source is None or source.get("authority_role") != "primary_legal":
            raise WaitingPeriodMaterialRulesCertificationError("material-rule evidence must remain primary_legal")
        registration_path = _safe_relative(source.get("registration_output_path"), "registration_output_path")
        registration, _ = _load(root, registration_path, f"registration[{document_id}]")
        candidate_id = _text(entry.get("candidate_id"), "binding_evidence.candidate_id")
        candidate = _candidate_index(registration).get(candidate_id)
        if candidate is None or candidate.get("text_sha256") != entry.get("candidate_text_sha256"):
            raise WaitingPeriodMaterialRulesCertificationError(f"candidate lineage mismatch: {candidate_id}")
        candidate_context[candidate_id] = (_mapping(registration.get("document"), "registration.document"), candidate)

    groups: dict[str, list[Mapping[str, Any]]] = {"relationship_rule": [], "applicability_condition": []}
    for raw in _items(manifest.get("material_rules"), "binding_manifest.material_rules"):
        rule = _mapping(raw, "material_rule")
        component_id = "relationship_rule" if rule.get("rule_type") == "RELATIONSHIP_LONGER_OF" else "applicability_condition"
        groups[component_id].append(rule)
    groups = {key: value for key, value in groups.items() if value}
    if not groups:
        raise WaitingPeriodMaterialRulesCertificationError("no material rules to certify")

    binding_id = _text(manifest.get("binding_id"), "binding_id")
    case_id = f"waiting_period_material_rules:{binding_id}"
    packages: list[EvidencePackage] = []
    requirements: list[RequirementResult] = []
    component_defs = {
        "relationship_rule": "WAITING_PERIOD_RELATIONSHIP_RULE",
        "applicability_condition": "WAITING_PERIOD_APPLICABILITY_CONDITION",
    }
    for component_id, rules in groups.items():
        requirement_id = f"requirement:{case_id}:{component_id}"
        evidence_ids: list[str] = []
        for rule_index, rule in enumerate(rules):
            statement = _text(rule.get("statement"), "material_rule.statement")
            for candidate_id in (_text(v, "evidence_candidate_ids[]") for v in _items(rule.get("evidence_candidate_ids"), "evidence_candidate_ids")):
                document, candidate = candidate_context[candidate_id]
                evidence_id = f"evidence:{case_id}:{component_id}:{rule_index}:{candidate_id}"
                evidence_ids.append(evidence_id)
                packages.append(EvidencePackage(
                    evidence_id=evidence_id,
                    requirement_id=requirement_id,
                    subject_reference=f"waiting_period_material_rules_binding:{binding_id}",
                    governed_entity_reference=f"waiting_period_material_rules_binding:{binding_id}",
                    field_or_topic=component_defs[component_id],
                    claim=statement,
                    evidence_role="DEFINING",
                    source_type=_text(document.get("document_type"), "document.document_type").upper(),
                    document_reference=_text(document.get("document_id"), "document.document_id"),
                    document_version=_text(document.get("document_version_id"), "document.document_version_id"),
                    effective_from=None,
                    effective_to=None,
                    page=candidate.get("source_page"),
                    section="Waiting period",
                    source_excerpt=_text(candidate.get("excerpt"), "candidate.excerpt"),
                    normalized_fact_reference=f"{binding_id}:{component_id}:{rule_index}",
                    authority_rank=1,
                    authority_requirement="AUTHORITATIVE",
                    version_status="CURRENT_APPLICABLE",
                    applicability_status="APPLICABLE",
                    lineage=Lineage(source_artifact_path=_text(document.get("storage_locator"), "document.storage_locator"), source_artifact_sha256=_text(document.get("content_sha256"), "document.content_sha256"), governed_record_path=relative_spec, governed_record_sha256=spec_sha, binding_reference=f"waiting_period_material_rules_binding:{binding_id}", projection_reference=f"waiting_period_material_rules:{component_id}", lineage_status="VERIFIED"),
                    retrieval_basis=("reviewed_waiting_period_material_rules_binding", _text(rule.get("rule_id"), "material_rule.rule_id"), candidate_id),
                    confidence=1.0,
                ))
        requirements.append(_requirement(requirement_id, tuple(evidence_ids)))

    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference=f"waiting_period_material_rules_binding:{binding_id}",
        topic_id="waiting_period_material_rules",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(build_component_certification_expectation(component_id=component_id, acceptable_statuses=("SATISFIED",)) for component_id in groups),
    )
    output = EvidenceResolverOutput(contract_version="1.0", request_id=f"request:{case_id}", resolution_id=f"resolution:{case_id}", evidence_packages=tuple(packages), requirement_results=tuple(requirements), entity_resolutions=(), document_resolutions=(), conflicts=(), missing_evidence=(), sufficiency="COMPLETE", limitations=("Material-rule certification does not publish the waiting period or determine customer-specific claim outcomes.",), resolution_trace=(), resolution_status="RESOLVED", confidence=1.0)
    return RuleCertificationCaseFixture(case_id=case_id, description=f"Material waiting-period rule certification for {binding_id}.", domain="health", expectation=expectation, evidence_output=output, expected_outcome="PASS")


def run_waiting_period_material_rules_certification_case(case: RuleCertificationCaseFixture) -> RuleCertificationResult:
    required_components = tuple(item.component_id for item in case.expectation.component_expectations)
    return run_rule_certification(expectation=case.expectation, evidence_output=case.evidence_output, domain=case.domain, registry=_registry(required_components))


__all__ = ["WaitingPeriodMaterialRulesCertificationError", "build_waiting_period_material_rules_certification_case", "run_waiting_period_material_rules_certification_case"]
