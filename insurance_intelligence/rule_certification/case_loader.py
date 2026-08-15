"""Strict insurer-independent loader for governed rule-certification case data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
    validate_output,
)
from insurance_intelligence.contracts.rule_certification import (
    build_component_certification_expectation,
    build_rule_certification_expectation,
)
from insurance_intelligence.rule_certification.fixtures import RuleCertificationCaseFixture


class RuleCertificationCaseLoadError(ValueError):
    """Raised when governed certification-case data cannot be materialized safely."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuleCertificationCaseLoadError(f"{label} must be an object")
    return value


def _keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise RuleCertificationCaseLoadError(f"{label} keys invalid: " + ", ".join(details))


def _tuple_strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuleCertificationCaseLoadError(f"{label} must be an array of strings")
    return tuple(value)


def _lineage(payload: object) -> Lineage:
    data = _mapping(payload, "evidence.lineage")
    _keys(
        data,
        {
            "source_artifact_path",
            "source_artifact_sha256",
            "governed_record_path",
            "governed_record_sha256",
            "binding_reference",
            "projection_reference",
            "lineage_status",
        },
        "evidence.lineage",
    )
    return Lineage(**data)


def _evidence(payload: object) -> EvidencePackage:
    data = dict(_mapping(payload, "evidence_package"))
    _keys(
        data,
        {
            "evidence_id",
            "requirement_id",
            "subject_reference",
            "governed_entity_reference",
            "field_or_topic",
            "claim",
            "evidence_role",
            "source_type",
            "document_reference",
            "document_version",
            "effective_from",
            "effective_to",
            "page",
            "section",
            "source_excerpt",
            "normalized_fact_reference",
            "authority_rank",
            "authority_requirement",
            "version_status",
            "applicability_status",
            "lineage",
            "retrieval_basis",
            "confidence",
        },
        "evidence_package",
    )
    data["lineage"] = _lineage(data["lineage"])
    data["retrieval_basis"] = _tuple_strings(data["retrieval_basis"], "evidence_package.retrieval_basis")
    return EvidencePackage(**data)


def _requirement(payload: object) -> RequirementResult:
    data = dict(_mapping(payload, "requirement_result"))
    _keys(
        data,
        {
            "requirement_id",
            "status",
            "matched_evidence_ids",
            "rejected_candidate_ids",
            "missing_reason",
            "authority_satisfied",
            "version_satisfied",
            "lineage_satisfied",
            "conflict_status",
            "confidence",
        },
        "requirement_result",
    )
    data["matched_evidence_ids"] = _tuple_strings(data["matched_evidence_ids"], "requirement_result.matched_evidence_ids")
    data["rejected_candidate_ids"] = _tuple_strings(data["rejected_candidate_ids"], "requirement_result.rejected_candidate_ids")
    return RequirementResult(**data)


def load_rule_certification_case(payload: Mapping[str, Any]) -> RuleCertificationCaseFixture:
    """Materialize one governed JSON case into the existing generic certification contracts."""
    data = _mapping(payload, "case")
    _keys(
        data,
        {"schema_version", "case_id", "description", "domain", "expected_outcome", "expectation", "evidence_output"},
        "case",
    )
    if data["schema_version"] != "1.0":
        raise RuleCertificationCaseLoadError("case.schema_version must be '1.0'")

    expectation_data = _mapping(data["expectation"], "case.expectation")
    _keys(
        expectation_data,
        {
            "contract_version",
            "certification_id",
            "governed_subject_reference",
            "topic_id",
            "topic_version",
            "expected_completeness_statuses",
            "expected_explanation_permitted",
            "component_expectations",
        },
        "case.expectation",
    )
    component_payloads = expectation_data["component_expectations"]
    if not isinstance(component_payloads, list):
        raise RuleCertificationCaseLoadError("case.expectation.component_expectations must be an array")
    components = []
    for index, item in enumerate(component_payloads):
        component = _mapping(item, f"case.expectation.component_expectations[{index}]")
        _keys(component, {"component_id", "acceptable_statuses"}, f"case.expectation.component_expectations[{index}]")
        components.append(
            build_component_certification_expectation(
                component_id=component["component_id"],
                acceptable_statuses=_tuple_strings(component["acceptable_statuses"], "acceptable_statuses"),
            )
        )
    expectation = build_rule_certification_expectation(
        contract_version=expectation_data["contract_version"],
        certification_id=expectation_data["certification_id"],
        governed_subject_reference=expectation_data["governed_subject_reference"],
        topic_id=expectation_data["topic_id"],
        topic_version=expectation_data["topic_version"],
        expected_completeness_statuses=_tuple_strings(
            expectation_data["expected_completeness_statuses"],
            "case.expectation.expected_completeness_statuses",
        ),
        expected_explanation_permitted=expectation_data["expected_explanation_permitted"],
        component_expectations=tuple(components),
    )

    output_data = _mapping(data["evidence_output"], "case.evidence_output")
    _keys(
        output_data,
        {
            "contract_version",
            "request_id",
            "resolution_id",
            "evidence_packages",
            "requirement_results",
            "missing_evidence",
            "sufficiency",
            "limitations",
            "resolution_status",
            "confidence",
        },
        "case.evidence_output",
    )
    evidence_payloads = output_data["evidence_packages"]
    requirement_payloads = output_data["requirement_results"]
    if not isinstance(evidence_payloads, list) or not isinstance(requirement_payloads, list):
        raise RuleCertificationCaseLoadError("evidence_packages and requirement_results must be arrays")
    output = EvidenceResolverOutput(
        contract_version=output_data["contract_version"],
        request_id=output_data["request_id"],
        resolution_id=output_data["resolution_id"],
        evidence_packages=tuple(_evidence(item) for item in evidence_payloads),
        requirement_results=tuple(_requirement(item) for item in requirement_payloads),
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=_tuple_strings(output_data["missing_evidence"], "case.evidence_output.missing_evidence"),
        sufficiency=output_data["sufficiency"],
        limitations=_tuple_strings(output_data["limitations"], "case.evidence_output.limitations"),
        resolution_trace=(),
        resolution_status=output_data["resolution_status"],
        confidence=output_data["confidence"],
    )
    validate_output(output)

    expected_outcome = data["expected_outcome"]
    if expected_outcome not in {"PASS", "FAIL", "BLOCKED"}:
        raise RuleCertificationCaseLoadError("case.expected_outcome must be PASS, FAIL, or BLOCKED")
    for label in ("case_id", "description", "domain"):
        if not isinstance(data[label], str) or not data[label].strip():
            raise RuleCertificationCaseLoadError(f"case.{label} must be a non-empty string")

    return RuleCertificationCaseFixture(
        case_id=data["case_id"].strip(),
        description=data["description"].strip(),
        domain=data["domain"].strip(),
        expectation=expectation,
        evidence_output=output,
        expected_outcome=expected_outcome,
    )


def load_rule_certification_case_file(path: str | Path) -> RuleCertificationCaseFixture:
    """Load one UTF-8 governed JSON case file and validate it through existing contracts."""
    file_path = Path(path)
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuleCertificationCaseLoadError(f"could not load certification case: {exc}") from exc
    try:
        return load_rule_certification_case(_mapping(payload, "case"))
    except (TypeError, ValueError) as exc:
        if isinstance(exc, RuleCertificationCaseLoadError):
            raise
        raise RuleCertificationCaseLoadError(str(exc)) from exc


__all__ = ["RuleCertificationCaseLoadError", "load_rule_certification_case", "load_rule_certification_case_file"]
