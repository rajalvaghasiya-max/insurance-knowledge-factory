"""Generic certification for multi-span resolved scalar waiting-period mechanics."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.canonical.waiting_period_multispan_binding import WaitingPeriodMultispanBinding
from insurance_intelligence.contracts.evidence import EvidencePackage, EvidenceResolverOutput, Lineage, RequirementResult
from insurance_intelligence.contracts.rule_certification import RuleCertificationResult, build_component_certification_expectation, build_rule_certification_expectation
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture
from insurance_intelligence.rule_certification.runner import run_rule_certification


class WaitingPeriodMultispanCertificationError(ValueError):
    pass


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodMultispanCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodMultispanCertificationError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodMultispanCertificationError(f"{label} must be non-empty text")
    return value.strip()


def _safe_relative(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise WaitingPeriodMultispanCertificationError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative).resolve()
    path.relative_to(root)
    raw = path.read_bytes()
    return _mapping(json.loads(raw.decode("utf-8")), label), sha256(raw).hexdigest()


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "evidence_review")
    return {_text(c.get("candidate_id"), "candidate_id"): c for c in (_mapping(raw, "candidate") for raw in _items(review.get("candidates"), "candidates"))}


def _requirement(requirement_id: str, evidence_ids: tuple[str, ...]) -> RequirementResult:
    return RequirementResult(requirement_id=requirement_id, status="SATISFIED", matched_evidence_ids=evidence_ids, rejected_candidate_ids=(), missing_reason=None, authority_satisfied=True, version_satisfied=True, lineage_satisfied=True, conflict_status="NONE", confidence=1.0)


def build_waiting_period_multispan_certification_case(*, binding_spec_path: str | Path, repository_root: str | Path) -> RuleCertificationCaseFixture:
    root = Path(repository_root).resolve()
    relative_spec = _safe_relative(str(binding_spec_path), "binding_spec_path")
    spec, spec_sha = _load(root, relative_spec, "binding_spec")
    if spec.get("binding_type") != "waiting_period_multispan_binding_v1" or spec.get("reviewed_by_human") is not True:
        raise WaitingPeriodMultispanCertificationError("binding spec is not review-ready")
    result = WaitingPeriodMultispanBinding().bind(spec=spec, repository_root=root, bound_at="1970-01-01T00:00:00+00:00")
    manifest = _mapping(result.manifest, "binding_manifest")
    if manifest.get("binding_status") != "reviewed_waiting_period_bound_not_published" or manifest.get("publication_status") != "bound_not_published":
        raise WaitingPeriodMultispanCertificationError("binding must remain reviewed and unpublished")

    bundle_path = _safe_relative(manifest.get("generic_source_bundle_path"), "generic_source_bundle_path")
    bundle, _ = _load(root, bundle_path, "generic_source_bundle")
    sources = {_text(s.get("document_id"), "source.document_id"): s for s in (_mapping(raw, "source") for raw in _items(bundle.get("sources"), "sources"))}
    candidates: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
    for raw in _items(manifest.get("evidence"), "evidence"):
        entry = _mapping(raw, "binding_evidence")
        document_id = _text(entry.get("document_id"), "document_id")
        source = sources.get(document_id)
        if source is None or source.get("authority_role") != "primary_legal":
            raise WaitingPeriodMultispanCertificationError("all certification evidence must remain primary_legal")
        registration_path = _safe_relative(source.get("registration_output_path"), "registration_output_path")
        registration, _ = _load(root, registration_path, f"registration[{document_id}]")
        candidate_id = _text(entry.get("candidate_id"), "candidate_id")
        candidate = _candidate_index(registration).get(candidate_id)
        if candidate is None or candidate.get("text_sha256") != entry.get("candidate_text_sha256"):
            raise WaitingPeriodMultispanCertificationError(f"candidate lineage mismatch: {candidate_id}")
        if candidate_id in candidates:
            raise WaitingPeriodMultispanCertificationError(f"duplicate candidate ID: {candidate_id}")
        candidates[candidate_id] = (_mapping(registration.get("document"), "document"), candidate)

    mechanic = _mapping(manifest.get("mechanic"), "mechanic")
    binding_id = _text(manifest.get("binding_id"), "binding_id")
    case_id = f"waiting_period_multispan:{binding_id}"
    subjects = tuple(_text(v, "applies_to[]") for v in _items(mechanic.get("applies_to"), "applies_to"))
    scope_bits = [f"scope_type={mechanic.get('scope_type')}"]
    if mechanic.get("scope_reference"):
        scope_bits.append(f"scope_reference={mechanic.get('scope_reference')}")
    if mechanic.get("sum_insured_enhancement_effect"):
        scope_bits.append(f"sum_insured_enhancement_effect={mechanic.get('sum_insured_enhancement_effect')}")
    claims: dict[str, tuple[str, str]] = {
        "waiting_period_duration": ("WAITING_PERIOD_DURATION", f"The waiting period duration is {mechanic.get('duration_value')} {mechanic.get('duration_unit')}."),
        "waiting_period_subject": ("WAITING_PERIOD_SUBJECT", "Waiting period applies to: " + "; ".join(subjects) + "."),
        "start_basis": ("WAITING_PERIOD_START_BASIS", f"The waiting period start basis is {mechanic.get('start_basis')}."),
        "applicability_scope": ("APPLICABILITY_SCOPE", "Waiting-period applicability: " + "; ".join(scope_bits) + "."),
    }
    if mechanic.get("continuity_dependency"):
        claims["continuity_or_credit_rule"] = ("CONTINUITY_OR_CREDIT_RULE", _text(mechanic.get("continuity_dependency"), "continuity_dependency"))
    exceptions = tuple(_text(v, "exceptions[]") for v in _items(mechanic.get("exclusions_or_exceptions", []), "exceptions"))
    if exceptions:
        claims["exception_condition"] = ("EXCEPTION_CONDITION", "Waiting-period exceptions: " + "; ".join(exceptions) + ".")

    component_map = _mapping(spec.get("component_evidence_candidate_ids"), "component_evidence_candidate_ids")
    if set(component_map) != set(claims):
        raise WaitingPeriodMultispanCertificationError(f"component evidence map must exactly cover certified components; missing={sorted(set(claims)-set(component_map))!r}; extra={sorted(set(component_map)-set(claims))!r}")

    packages: list[EvidencePackage] = []
    requirements: list[RequirementResult] = []
    for component_id, (requirement_type, claim) in claims.items():
        candidate_ids = tuple(_text(v, f"{component_id}[]") for v in _items(component_map.get(component_id), component_id))
        if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
            raise WaitingPeriodMultispanCertificationError(f"component {component_id} must map to unique candidate IDs")
        evidence_ids: list[str] = []
        for candidate_id in candidate_ids:
            resolved = candidates.get(candidate_id)
            if resolved is None:
                raise WaitingPeriodMultispanCertificationError(f"component {component_id} references unbound candidate {candidate_id}")
            document, candidate = resolved
            evidence_id = f"evidence:{case_id}:{component_id}:{candidate_id}"
            evidence_ids.append(evidence_id)
            packages.append(EvidencePackage(evidence_id=evidence_id, requirement_id=f"requirement:{case_id}:{component_id}", subject_reference=f"waiting_period_multispan_binding:{binding_id}", governed_entity_reference=f"waiting_period_multispan_binding:{binding_id}", field_or_topic=requirement_type, claim=claim, evidence_role="DEFINING", source_type=_text(document.get("document_type"), "document_type").upper(), document_reference=_text(document.get("document_id"), "document_id"), document_version=_text(document.get("document_version_id"), "document_version_id"), effective_from=None, effective_to=None, page=candidate.get("source_page"), section="Waiting period", source_excerpt=_text(candidate.get("excerpt"), "excerpt"), normalized_fact_reference=f"{binding_id}:{component_id}", authority_rank=1, authority_requirement="AUTHORITATIVE", version_status="CURRENT_APPLICABLE", applicability_status="APPLICABLE", lineage=Lineage(source_artifact_path=_text(document.get("storage_locator"), "storage_locator"), source_artifact_sha256=_text(document.get("content_sha256"), "content_sha256"), governed_record_path=relative_spec, governed_record_sha256=spec_sha, binding_reference=f"waiting_period_multispan_binding:{binding_id}", projection_reference=f"waiting_period:{component_id}", lineage_status="VERIFIED"), retrieval_basis=("reviewed_waiting_period_multispan_binding", "mechanism", candidate_id), confidence=1.0))
        requirements.append(_requirement(f"requirement:{case_id}:{component_id}", tuple(evidence_ids)))

    expectation = build_rule_certification_expectation(certification_id=case_id, governed_subject_reference=f"waiting_period_multispan_binding:{binding_id}", topic_id="waiting_period", topic_version="1.0", expected_completeness_statuses=("COMPLETE",), expected_explanation_permitted=True, component_expectations=tuple(build_component_certification_expectation(component_id=k, acceptable_statuses=("SATISFIED",)) for k in claims))
    output = EvidenceResolverOutput(contract_version="1.0", request_id=f"request:{case_id}", resolution_id=f"resolution:{case_id}", evidence_packages=tuple(packages), requirement_results=tuple(requirements), entity_resolutions=(), document_resolutions=(), conflicts=(), missing_evidence=(), sufficiency="COMPLETE", limitations=("Multispan certification preserves exact component-to-candidate attribution and does not publish or determine customer-specific claim outcomes.",), resolution_trace=(), resolution_status="RESOLVED", confidence=1.0)
    return RuleCertificationCaseFixture(case_id=case_id, description=f"Multi-span waiting-period certification for {binding_id}.", domain="health", expectation=expectation, evidence_output=output, expected_outcome="PASS")


def run_waiting_period_multispan_certification_case(case: RuleCertificationCaseFixture) -> RuleCertificationResult:
    return run_rule_certification(expectation=case.expectation, evidence_output=case.evidence_output, domain=case.domain)


__all__ = ["WaitingPeriodMultispanCertificationError", "build_waiting_period_multispan_certification_case", "run_waiting_period_multispan_certification_case"]
