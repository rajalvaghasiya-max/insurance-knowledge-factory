"""Certification extension for resolved waiting periods with typed modifications."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from insurance_intelligence.contracts.evidence import RequirementResult
from insurance_intelligence.contracts.rule_certification import (
    RuleCertificationResult,
    build_component_certification_expectation,
    build_rule_certification_expectation,
)
from insurance_intelligence.contracts.topic_completeness import build_component_definition, build_topic_definition
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.rule_certification.waiting_period import build_waiting_period_certification_case
from insurance_intelligence.rule_certification.waiting_period_multispan import build_waiting_period_multispan_certification_case
from insurance_intelligence.topic_completeness.catalogue import build_waiting_period_definition
from insurance_intelligence.topic_completeness.registry import TopicCompletenessRegistry


class WaitingPeriodModificationCertificationError(ValueError):
    pass


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodModificationCertificationError(f"{label} must be non-empty text")
    return value.strip()


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WaitingPeriodModificationCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise WaitingPeriodModificationCertificationError(f"{label} must be a JSON array")
    return value


def _modification_claim(modifications: Sequence[Mapping[str, Any]]) -> str:
    claims: list[str] = []
    for index, raw in enumerate(modifications):
        item = _mapping(raw, f"modifications[{index}]")
        modification_type = _text(item.get("modification_type"), f"modifications[{index}].modification_type")
        condition = _text(item.get("condition"), f"modifications[{index}].condition")
        value = item.get("resulting_duration_value")
        if type(value) is not int or value < 0:
            raise WaitingPeriodModificationCertificationError(f"modifications[{index}].resulting_duration_value must be a non-negative integer")
        unit = _text(item.get("resulting_duration_unit"), f"modifications[{index}].resulting_duration_unit")
        claims.append(f"{modification_type} when {condition} => {value} {unit}")
    if not claims:
        raise WaitingPeriodModificationCertificationError("at least one waiting-period modification is required")
    return "Waiting-period modifications: " + "; ".join(claims) + "."


def _modification_candidate_ids(modifications: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    candidate_ids: list[str] = []
    for index, raw in enumerate(modifications):
        refs = _items(raw.get("evidence_reference_ids", []), f"modifications[{index}].evidence_reference_ids")
        for ref_index, value in enumerate(refs):
            ref = _text(value, f"modifications[{index}].evidence_reference_ids[{ref_index}]")
            parts = ref.split(":")
            if len(parts) != 3 or not parts[1]:
                raise WaitingPeriodModificationCertificationError("modification evidence references must use document_id:candidate_id:sha256")
            candidate_ids.append(parts[1])
    return tuple(dict.fromkeys(candidate_ids))


def _registry_with_modification_component() -> TopicCompletenessRegistry:
    base = build_waiting_period_definition()
    modification = build_component_definition(
        component_id="modification_rule",
        requirement_type="WAITING_PERIOD_MODIFICATION_RULE",
        required=False,
        acceptable_requirement_statuses=("SATISFIED", "SATISFIED_WITH_LIMITATIONS"),
        acceptable_evidence_roles=("SUPPORTING", "DEFINING", "QUALIFYING"),
        minimum_authority="AUTHORITATIVE",
        dependency_component_ids=("waiting_period_duration",),
        reason="Resolve any governed rule that changes the waiting-period duration under a stated condition.",
    )
    definition = build_topic_definition(topic_id=base.topic_id, topic_version=base.topic_version, domain=base.domain, components=(*base.components, modification))
    registry = TopicCompletenessRegistry()
    registry.register(definition, active=True)
    return registry


def augment_waiting_period_case_with_modifications(base_case: RuleCertificationCaseFixture, *, modifications: Sequence[Mapping[str, Any]]) -> RuleCertificationCaseFixture:
    if not isinstance(base_case, RuleCertificationCaseFixture) or base_case.expectation.topic_id != "waiting_period":
        raise WaitingPeriodModificationCertificationError("base_case must certify waiting_period")
    claim = _modification_claim(modifications)
    candidate_ids = _modification_candidate_ids(modifications)

    sources = []
    if candidate_ids:
        by_candidate = {}
        for package in base_case.evidence_output.evidence_packages:
            if package.retrieval_basis:
                candidate_id = package.retrieval_basis[-1]
                if candidate_id in candidate_ids and candidate_id not in by_candidate:
                    by_candidate[candidate_id] = package
        missing = [candidate_id for candidate_id in candidate_ids if candidate_id not in by_candidate]
        if missing:
            raise WaitingPeriodModificationCertificationError(
                f"modification evidence candidates are not represented by the governed base case: {missing!r}"
            )
        sources = [by_candidate[candidate_id] for candidate_id in candidate_ids]
    else:
        schedule_packages = tuple(
            package for package in base_case.evidence_output.evidence_packages
            if package.field_or_topic == "WAITING_PERIOD_DURATION"
            and len(package.retrieval_basis) >= 2
            and package.retrieval_basis[1] == "schedule_value_resolution"
        )
        if len(schedule_packages) != 1:
            raise WaitingPeriodModificationCertificationError(
                "modification certification requires explicit modification evidence or exactly one schedule_value_resolution duration evidence package"
            )
        sources = [schedule_packages[0]]

    requirement_id = f"requirement:{base_case.case_id}:modification_rule"
    packages = []
    evidence_ids = []
    for index, source in enumerate(sources):
        candidate_suffix = source.retrieval_basis[-1] if source.retrieval_basis else str(index)
        evidence_id = f"evidence:{base_case.case_id}:modification_rule:{candidate_suffix}"
        evidence_ids.append(evidence_id)
        packages.append(replace(source, evidence_id=evidence_id, requirement_id=requirement_id, field_or_topic="WAITING_PERIOD_MODIFICATION_RULE", claim=claim, normalized_fact_reference=f"{source.normalized_fact_reference}:modification_rule"))

    requirement = RequirementResult(requirement_id=requirement_id, status="SATISFIED", matched_evidence_ids=tuple(evidence_ids), rejected_candidate_ids=(), missing_reason=None, authority_satisfied=True, version_satisfied=True, lineage_satisfied=True, conflict_status="NONE", confidence=1.0)
    expectation = build_rule_certification_expectation(
        certification_id=base_case.expectation.certification_id,
        governed_subject_reference=base_case.expectation.governed_subject_reference,
        topic_id=base_case.expectation.topic_id,
        topic_version=base_case.expectation.topic_version,
        expected_completeness_statuses=base_case.expectation.expected_completeness_statuses,
        expected_explanation_permitted=base_case.expectation.expected_explanation_permitted,
        component_expectations=(*base_case.expectation.component_expectations, build_component_certification_expectation(component_id="modification_rule", acceptable_statuses=("SATISFIED",))),
    )
    output = replace(base_case.evidence_output, evidence_packages=(*base_case.evidence_output.evidence_packages, *packages), requirement_results=(*base_case.evidence_output.requirement_results, requirement))
    return replace(base_case, expectation=expectation, evidence_output=output)


def build_waiting_period_modification_certification_case(*, binding_spec_path: str | Path, repository_root: str | Path) -> RuleCertificationCaseFixture:
    root = Path(repository_root).resolve()
    relative = Path(binding_spec_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise WaitingPeriodModificationCertificationError("binding_spec_path must be repository-relative")
    path = (root / relative).resolve()
    path.relative_to(root)
    if not path.is_file():
        raise FileNotFoundError(f"binding specification was not found: {relative.as_posix()}")
    try:
        spec = _mapping(json.loads(path.read_text(encoding="utf-8")), "binding_spec")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WaitingPeriodModificationCertificationError("binding specification is not valid JSON") from exc
    mechanic = _mapping(spec.get("mechanic"), "binding_spec.mechanic")
    modifications = tuple(_mapping(item, "binding_spec.mechanic.modifications[]") for item in _items(mechanic.get("modifications", []), "binding_spec.mechanic.modifications"))
    if not modifications:
        raise WaitingPeriodModificationCertificationError("binding specification does not contain waiting-period modifications")

    binding_type = spec.get("binding_type")
    if binding_type == "waiting_period_binding_v1":
        base_case = build_waiting_period_certification_case(binding_spec_path=relative.as_posix(), repository_root=root)
    elif binding_type == "waiting_period_multispan_binding_v1":
        base_case = build_waiting_period_multispan_certification_case(binding_spec_path=relative.as_posix(), repository_root=root)
    else:
        raise WaitingPeriodModificationCertificationError(f"unsupported modification-bearing binding type {binding_type!r}")
    return augment_waiting_period_case_with_modifications(base_case, modifications=modifications)


def run_waiting_period_modification_certification_case(case: RuleCertificationCaseFixture) -> RuleCertificationResult:
    if not isinstance(case, RuleCertificationCaseFixture):
        raise WaitingPeriodModificationCertificationError("case must be a RuleCertificationCaseFixture")
    return run_rule_certification(expectation=case.expectation, evidence_output=case.evidence_output, registry=_registry_with_modification_component(), domain=case.domain)


__all__ = ["WaitingPeriodModificationCertificationError", "augment_waiting_period_case_with_modifications", "build_waiting_period_modification_certification_case", "run_waiting_period_modification_certification_case"]
