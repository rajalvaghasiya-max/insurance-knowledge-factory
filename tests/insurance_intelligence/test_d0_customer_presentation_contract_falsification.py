from __future__ import annotations

from dataclasses import fields

from insurance_intelligence.contracts import response as response_contract
from insurance_intelligence.response import human_answer


def test_d0_customer_presentation_contract_is_typed_before_rendering() -> None:
    """Freeze #345 at the first missing generic customer-presentation contract.

    This is intentionally structural rather than wording-based. A valid repair must
    create typed customer-facing semantics instead of filtering machine prose.
    """

    missing: list[str] = []

    output_fields = {item.name for item in fields(response_contract.ResponseAssemblerOutput)}
    if "customer_reason" not in output_fields:
        missing.append("ResponseAssemblerOutput.customer_reason")

    reason_type = getattr(response_contract, "CustomerReason", None)
    if reason_type is None:
        missing.append("CustomerReason")
    else:
        reason_fields = {item.name for item in fields(reason_type)}
        for required in (
            "reason_kind",
            "text",
            "resolving_requirement",
        ):
            if required not in reason_fields:
                missing.append(f"CustomerReason.{required}")

    reason_kinds = getattr(response_contract, "CUSTOMER_REASON_KINDS", frozenset())
    for required_kind in (
        "MISSING_CUSTOMER_FACT",
        "SOURCE_DOES_NOT_ESTABLISH",
    ):
        if required_kind not in reason_kinds:
            missing.append(f"CUSTOMER_REASON_KINDS[{required_kind}]")

    if "CUSTOMER_EXPLANATION" not in response_contract.SECTION_TYPES:
        missing.append("SECTION_TYPES[CUSTOMER_EXPLANATION]")

    human_meaning_types = getattr(
        human_answer,
        "_HUMAN_MEANING_SECTION_TYPES",
        frozenset(),
    )
    if "EXPLANATION" in human_meaning_types:
        missing.append("HumanAnswerView still admits raw EXPLANATION")
    if "CONDITION" in human_meaning_types:
        missing.append("HumanAnswerView still admits raw CONDITION")
    if "CUSTOMER_EXPLANATION" not in human_meaning_types:
        missing.append("HumanAnswerView lacks CUSTOMER_EXPLANATION")

    assert not missing, (
        "D0 customer-presentation semantic boundary is missing: "
        + ", ".join(missing)
    )
