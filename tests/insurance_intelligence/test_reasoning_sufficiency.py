from insurance_intelligence.contracts.reasoning import build_requirement_result
from insurance_intelligence.reasoning.sufficiency import (
    SufficiencyDecision,
    evaluate_reasoning_sufficiency,
)


def rr(status, *, requirement_id="r1", confidence=1.0, missing=(), reason=None):
    return build_requirement_result(
        requirement_id=requirement_id,
        status=status,
        evidence_satisfied=status != "BLOCKED_BY_EVIDENCE",
        context_satisfied=status != "BLOCKED_BY_CONTEXT",
        conflict_status="MATERIAL" if status == "CONFLICTING" else "NONE",
        confidence=confidence,
        missing_inputs=missing,
        unsupported_reason=reason,
    )


def test_no_results_maps_to_no_reasoning_required():
    assert evaluate_reasoning_sufficiency(()) == SufficiencyDecision(
        "UNSUPPORTED", "NO_REASONING_REQUIRED", 0.0, ()
    )


def test_all_satisfied_is_complete():
    decision = evaluate_reasoning_sufficiency((rr("SATISFIED"), rr("SATISFIED", requirement_id="r2")))
    assert decision.reasoning_sufficiency == "COMPLETE"
    assert decision.reasoning_status == "REASONED"


def test_satisfied_with_limitations_is_sufficient():
    decision = evaluate_reasoning_sufficiency((rr("SATISFIED_WITH_LIMITATIONS"),))
    assert decision.reasoning_sufficiency == "SUFFICIENT"
    assert decision.reasoning_status == "REASONED_WITH_LIMITATIONS"


def test_partial_has_partial_status():
    decision = evaluate_reasoning_sufficiency((rr("PARTIALLY_SATISFIED"),))
    assert decision.reasoning_sufficiency == "PARTIAL"
    assert decision.reasoning_status == "PARTIALLY_REASONED"


def test_conditional_has_conditional_status():
    decision = evaluate_reasoning_sufficiency((rr("CONDITIONAL"),))
    assert decision.reasoning_sufficiency == "CONDITIONAL"
    assert decision.reasoning_status == "CONDITIONAL"


def test_conflict_precedes_partial():
    decision = evaluate_reasoning_sufficiency((rr("PARTIALLY_SATISFIED"), rr("CONFLICTING", requirement_id="r2")))
    assert decision.reasoning_sufficiency == "CONFLICTING"
    assert decision.reasoning_status == "CONFLICTING"


def test_evidence_block_precedes_conflict():
    decision = evaluate_reasoning_sufficiency((rr("CONFLICTING"), rr("BLOCKED_BY_EVIDENCE", requirement_id="r2")))
    assert decision.reasoning_sufficiency == "BLOCKED"
    assert decision.reasoning_status == "NOT_REASONED"


def test_context_block_is_blocking():
    decision = evaluate_reasoning_sufficiency((rr("BLOCKED_BY_CONTEXT"),))
    assert decision.reasoning_sufficiency == "BLOCKED"


def test_no_applicable_rule_is_unsupported():
    decision = evaluate_reasoning_sufficiency((rr("NO_APPLICABLE_RULE"),))
    assert decision.reasoning_sufficiency == "UNSUPPORTED"
    assert decision.reasoning_status == "NOT_REASONED"


def test_supported_plus_unsupported_is_partial():
    decision = evaluate_reasoning_sufficiency((rr("SATISFIED"), rr("UNSUPPORTED", requirement_id="r2")))
    assert decision.reasoning_sufficiency == "PARTIAL"


def test_confidence_is_mean_for_complete_results():
    decision = evaluate_reasoning_sufficiency((rr("SATISFIED", confidence=.8), rr("SATISFIED", requirement_id="r2", confidence=.6)))
    assert decision.confidence == .7


def test_blocked_confidence_is_zero():
    decision = evaluate_reasoning_sufficiency((rr("BLOCKED_BY_EVIDENCE", confidence=1.0),))
    assert decision.confidence == 0.0


def test_conditional_confidence_is_penalized():
    decision = evaluate_reasoning_sufficiency((rr("CONDITIONAL", confidence=1.0),))
    assert decision.confidence == .85


def test_limitations_include_missing_inputs():
    decision = evaluate_reasoning_sufficiency((rr("BLOCKED_BY_CONTEXT", missing=("treatment_city",)),))
    assert decision.limitations[0] == "r1: missing inputs: treatment_city"


def test_limitations_include_unsupported_reason():
    decision = evaluate_reasoning_sufficiency((rr("UNSUPPORTED", reason="no registered rule"),))
    assert "r1: no registered rule" in decision.limitations


def test_limitations_are_deterministic_by_requirement_id():
    decision = evaluate_reasoning_sufficiency(
        (
            rr("UNSUPPORTED", requirement_id="z", reason="z reason"),
            rr("UNSUPPORTED", requirement_id="a", reason="a reason"),
        )
    )
    assert decision.limitations == ("a: a reason", "z: z reason")
