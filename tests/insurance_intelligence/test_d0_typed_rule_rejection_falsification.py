from __future__ import annotations

from dataclasses import fields

from insurance_intelligence.contracts import reasoning as reasoning_contract


def test_d0_rule_rejection_cause_is_typed_and_preserved() -> None:
    """Freeze #348 at the first missing generic rejection-cause contract."""

    missing: list[str] = []

    execution_fields = {item.name for item in fields(reasoning_contract.RuleExecution)}
    if "rejection_kind" not in execution_fields:
        missing.append("RuleExecution.rejection_kind")

    result_fields = {
        item.name for item in fields(reasoning_contract.RequirementReasoningResult)
    }
    if "rejection_kind" not in result_fields:
        missing.append("RequirementReasoningResult.rejection_kind")

    kinds = getattr(reasoning_contract, "RULE_REJECTION_KINDS", frozenset())
    for required in (
        "MISSING_CUSTOMER_FACT",
        "SOURCE_DOES_NOT_ESTABLISH",
        "UNSUPPORTED_REASONING",
    ):
        if required not in kinds:
            missing.append(f"RULE_REJECTION_KINDS[{required}]")

    assert not missing, (
        "D0 typed rule-rejection cause is missing: "
        + ", ".join(missing)
    )
