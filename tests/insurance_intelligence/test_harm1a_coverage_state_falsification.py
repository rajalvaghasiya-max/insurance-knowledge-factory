import json
from pathlib import Path

from factory_core.rules.conditional_rule_evaluation_models import ApplicabilityStatus
from insurance_intelligence.contracts.evidence import (
    APPLICABILITY_STATUSES,
    CONFLICT_RESOLUTION_STATUSES,
)
from insurance_intelligence.contracts.reasoning import (
    FINDING_STATUSES,
    FINDING_TYPES,
    REQUIREMENT_REASONING_STATUSES,
    build_finding,
)
from insurance_intelligence.contracts.response import (
    RESPONSE_STATUSES,
    build_evidence_reference,
    build_output,
    build_section,
)
from insurance_intelligence.reasoning.rules import rule_definitions
from knowledge_domains.health.waiting_period_timeline.waiting_period_timeline_simulation_cell import (
    WaitingPeriodTimelineSimulationCell,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPOSITORY_ROOT / "docs/architecture/HARM_1A_COVERAGE_STATE_FALSIFICATION_SPEC.json"

EXPECTED_OUTCOMES = {
    "COVERED_NOW",
    "NOT_COVERED_YET",
    "EXCLUDED_BY_CURRENT_WORDING",
    "COVERED_ONLY_IF",
    "INSTANCE_OR_SCHEDULE_DEPENDENT",
    "CANNOT_DETERMINE_YET",
}

EXPECTED_CLASSIFICATIONS = {
    "FOUND_AND_REPRESENTABLE",
    "FOUND_BUT_AMBIGUOUS_SCOPE",
    "FOUND_AND_NOT_REPRESENTABLE",
    "CURRENT_SOURCE_MANUFACTURING_GAP",
    "INSTANCE_OR_SCHEDULE_CONTEXT_REQUIRED",
}


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _source_text(scenario: dict) -> str:
    source = scenario["source"]
    document = json.loads((REPOSITORY_ROOT / source["path"]).read_text(encoding="utf-8"))

    if source["record_kind"] == "core_benefit":
        record = document["core_benefits"][source["record_key"]]
        assert record["value"] is True
        assert record["validated"] is True
        return record["raw_text"]

    if source["record_kind"] == "exclusion":
        record = next(item for item in document["exclusions"] if item["code"] == source["record_key"])
        return record["description"]

    if source["record_kind"] == "unresolved_item":
        record = next(
            item
            for item in document["unresolved_items"]
            if item["waiting_period_type"] == source["record_key"]
        )
        return f'{record["status"]} {record["reason"]}'

    raise AssertionError(f'Unsupported record_kind: {source["record_kind"]}')


def _finding(*, finding_type: str, status: str, predicate: str, effect: str, condition: str | None = None):
    return build_finding(
        finding_id=f"finding:{predicate}",
        requirement_id="requirement:harm1a",
        finding_type=finding_type,
        subject="activ_one",
        predicate=predicate,
        object_or_effect=effect,
        condition=condition,
        scope="current_policy_wording",
        finding_status=status,
        derivation_type=("CONDITIONAL_DERIVATION" if status == "CONDITIONAL" else "DIRECT_FACT"),
        rule_id="harm1a_existing_contract_pressure",
        rule_version="1.0",
        evidence_ids=(f"evidence:{predicate}",),
        limitations=("Claim approval and payment are not determined by this finding.",),
        confidence=0.9,
    )


def _answer(*, response_id: str, finding_id: str, answer: str):
    reference_id = f"reference:{finding_id}"
    return build_output(
        request_id="request:harm1a",
        response_id=response_id,
        response_status="ANSWER_WITH_LIMITATIONS",
        audience="consumer",
        response_format="STANDARD",
        direct_answer=answer,
        sections=(
            build_section(
                section_id=f"section:{finding_id}",
                section_type="DIRECT_ANSWER",
                status="INCLUDED",
                text=answer,
                approved_finding_ids=(finding_id,),
                evidence_reference_ids=(reference_id,),
                limitation_ids=("limitation:claim-non-guarantee",),
            ),
        ),
        evidence_references=(
            build_evidence_reference(
                reference_id=reference_id,
                reference_type="FINDING",
                source_id=finding_id,
                label="HARM-1A evidence-backed finding",
                approved_finding_ids=(finding_id,),
            ),
        ),
        limitations=("This answer does not determine claim approval or payment.",),
        confidence=0.9,
    )


def test_falsification_spec_is_complete_and_closes_no_architecture_gate() -> None:
    spec = _spec()

    assert set(spec["pre_registered_user_outcomes"]) == EXPECTED_OUTCOMES
    assert set(spec["acceptance_classifications"]) == EXPECTED_CLASSIFICATIONS
    assert {item["user_outcome"] for item in spec["scenarios"]} == EXPECTED_OUTCOMES
    assert len({item["scenario_id"] for item in spec["scenarios"]}) == len(EXPECTED_OUTCOMES)

    gate = spec["architecture_falsification_rule"]
    assert gate["found_and_not_representable_count"] == 0
    assert gate["result"] == "NOT_TRIGGERED"
    assert all(item["classification"] != "FOUND_AND_NOT_REPRESENTABLE" for item in spec["scenarios"])
    assert spec["bounded_conclusion"]["runtime_architecture_change"] == "NOT_AUTHORIZED"


def test_every_scenario_is_bound_to_current_repository_evidence() -> None:
    for scenario in _spec()["scenarios"]:
        text = _source_text(scenario)
        for fragment in scenario["source"]["required_fragments"]:
            assert fragment.casefold() in text.casefold(), (scenario["scenario_id"], fragment)


def test_existing_contract_vocabulary_preserves_each_reason_for_the_outcome() -> None:
    assert {"COVERAGE_EFFECT", "COVERAGE_CONDITION", "EXCLUSION_EFFECT", "UNRESOLVED_IMPLICATION"} <= FINDING_TYPES
    assert {"SUPPORTED", "SUPPORTED_WITH_LIMITATIONS", "CONDITIONAL", "PARTIALLY_SUPPORTED"} <= FINDING_STATUSES
    assert {"POLICY_SPECIFIC_OVERRIDE", "DATE_UNRESOLVED", "VARIANT_UNRESOLVED"} <= APPLICABILITY_STATUSES
    assert "REQUIRES_POLICY_SCHEDULE" in CONFLICT_RESOLUTION_STATUSES
    assert {"BLOCKED_BY_EVIDENCE", "BLOCKED_BY_CONTEXT"} <= REQUIREMENT_REASONING_STATUSES
    assert {"ANSWER_WITH_LIMITATIONS", "CLARIFICATION_REQUIRED", "INSUFFICIENT_EVIDENCE"} <= RESPONSE_STATUSES
    assert {ApplicabilityStatus.APPLIES, ApplicabilityStatus.INDETERMINATE} <= set(ApplicabilityStatus)


def test_existing_finding_contract_does_not_flatten_not_yet_never_and_only_if() -> None:
    findings = (
        _finding(
            finding_type="COVERAGE_EFFECT",
            status="SUPPORTED_WITH_LIMITATIONS",
            predicate="documented_policy_benefit",
            effect="in-patient treatment is documented as a policy benefit",
        ),
        _finding(
            finding_type="COVERAGE_CONDITION",
            status="SUPPORTED_WITH_LIMITATIONS",
            predicate="waiting_period_active",
            effect="coverage activation is delayed until the waiting period is complete",
            condition="24 months of continuous coverage",
        ),
        _finding(
            finding_type="EXCLUSION_EFFECT",
            status="SUPPORTED",
            predicate="excluded_by_current_wording",
            effect="admission primarily for diagnostics or evaluation is excluded",
        ),
        _finding(
            finding_type="COVERAGE_CONDITION",
            status="CONDITIONAL",
            predicate="covered_only_if",
            effect="obesity surgery requires every documented condition",
            condition="all policy conditions are satisfied",
        ),
        _finding(
            finding_type="UNRESOLVED_IMPLICATION",
            status="PARTIALLY_SUPPORTED",
            predicate="requires_policy_schedule",
            effect="policy-specific applicability cannot be concluded",
            condition="Policy Schedule is available",
        ),
    )

    signatures = {
        (item.finding_type, item.finding_status, item.predicate, item.condition)
        for item in findings
    }
    assert len(signatures) == 5
    assert findings[1].predicate == "waiting_period_active"
    assert findings[2].finding_type == "EXCLUSION_EFFECT"
    assert findings[3].finding_status == "CONDITIONAL"
    assert findings[4].finding_type == "UNRESOLVED_IMPLICATION"


def test_response_contract_supports_safe_answers_clarification_and_insufficient_evidence() -> None:
    spec_by_outcome = {item["user_outcome"]: item for item in _spec()["scenarios"]}
    answer_findings = {
        "COVERED_NOW": _finding(
            finding_type="COVERAGE_EFFECT",
            status="SUPPORTED_WITH_LIMITATIONS",
            predicate="documented_policy_benefit",
            effect="documented benefit",
        ),
        "NOT_COVERED_YET": _finding(
            finding_type="COVERAGE_CONDITION",
            status="SUPPORTED_WITH_LIMITATIONS",
            predicate="waiting_period_active",
            effect="temporary waiting restriction",
            condition="waiting period is complete",
        ),
        "EXCLUDED_BY_CURRENT_WORDING": _finding(
            finding_type="EXCLUSION_EFFECT",
            status="SUPPORTED",
            predicate="excluded_by_current_wording",
            effect="current-wording exclusion",
        ),
        "COVERED_ONLY_IF": _finding(
            finding_type="COVERAGE_CONDITION",
            status="CONDITIONAL",
            predicate="covered_only_if",
            effect="conditional coverage",
            condition="all documented conditions are satisfied",
        ),
    }

    for outcome, finding in answer_findings.items():
        response = _answer(
            response_id=f"response:{outcome.lower()}",
            finding_id=finding.finding_id,
            answer=spec_by_outcome[outcome]["safe_answer"],
        )
        assert response.response_status == "ANSWER_WITH_LIMITATIONS"
        assert response.direct_answer
        assert response.limitations

    clarification = build_output(
        request_id="request:harm1a",
        response_id="response:schedule",
        response_status="CLARIFICATION_REQUIRED",
        audience="consumer",
        response_format="STANDARD",
        sections=(
            build_section(
                section_id="section:schedule",
                section_type="CLARIFICATION",
                status="INCLUDED",
                text="Please provide the applicable Policy Schedule.",
                clarification_ids=("clarification:policy-schedule",),
            ),
        ),
        clarification_questions=("Does the Policy Schedule cover treatment outside India?",),
        confidence=0.0,
    )
    unknown = build_output(
        request_id="request:harm1a",
        response_id="response:unknown",
        response_status="INSUFFICIENT_EVIDENCE",
        audience="consumer",
        response_format="STANDARD",
        limitations=("The exact clause and activation boundary are not governed.",),
        confidence=0.0,
    )

    assert clarification.direct_answer is None
    assert clarification.clarification_questions
    assert unknown.direct_answer is None
    assert unknown.sections == ()
    assert unknown.evidence_references == ()


def test_waiting_period_timeline_preserves_not_yet_vs_timeline_complete(tmp_path: Path) -> None:
    cell = WaitingPeriodTimelineSimulationCell(output_dir=tmp_path)

    before_paths = cell.run(
        policy_start_date="2026-01-01",
        claim_date="2026-12-31",
        waiting_period_type="reduced_specific_disease_waiting_period",
        waiting_period_value=1,
        waiting_period_unit="years",
        activation_convention="AFTER_COMPLETION_OF_PERIOD",
    )
    before = json.loads(Path(before_paths["asset"]).read_text(encoding="utf-8"))

    after_paths = cell.run(
        policy_start_date="2026-01-01",
        claim_date="2027-01-02",
        waiting_period_type="reduced_specific_disease_waiting_period",
        waiting_period_value=1,
        waiting_period_unit="years",
        activation_convention="AFTER_COMPLETION_OF_PERIOD",
    )
    after = json.loads(Path(after_paths["asset"]).read_text(encoding="utf-8"))

    assert before["timeline_assessment"]["timeline_status"] == "NOT_ACTIVE"
    assert before["timeline_assessment"]["waiting_period_complete"] is False
    assert "does not appear complete yet" in before["explanation"]["what_this_means"]
    assert after["timeline_assessment"]["timeline_status"] == "ACTIVE"
    assert after["timeline_assessment"]["waiting_period_complete"] is True
    assert "does not confirm final claim approval" in after["explanation"]["what_this_does_not_mean"]


def test_runtime_rule_inventory_confirms_manufacturing_gap_without_architecture_claim() -> None:
    definitions = rule_definitions()
    topics = {item.topic for item in definitions}
    finding_types = {finding_type for item in definitions for finding_type in item.output_finding_types}

    assert topics == {"any", "conditional_copayment"}
    assert "EXCLUSION_EFFECT" not in finding_types
    assert "COVERAGE_EFFECT" not in finding_types
    assert _spec()["bounded_conclusion"] == {
        "representation_pressure": "NOT_PROVEN",
        "runtime_architecture_change": "NOT_AUTHORIZED",
        "manufacturing_pressure": "CONFIRMED",
        "next_step": (
            "Inspect the current Star Comprehensive restoration source shape "
            "before manufacturing any restoration rule."
        ),
    }
