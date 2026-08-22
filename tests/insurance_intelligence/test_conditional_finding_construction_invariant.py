from __future__ import annotations

import pytest

from insurance_intelligence.contracts.reasoning import (
    ReasoningContractError,
    build_finding,
)


def _base_kwargs() -> dict[str, object]:
    return {
        "finding_id": "finding_conditional_invariant",
        "requirement_id": "req_conditional_invariant",
        "finding_type": "CLAIM_COST_SHARING",
        "subject": "covered claim",
        "predicate": "requires",
        "object_or_effect": "member cost sharing",
        "scope": "policy wording",
        "finding_status": "SUPPORTED",
        "derivation_type": "DIRECT_FACT",
        "rule_id": "rule_conditional_invariant",
        "rule_version": "1.0",
        "evidence_ids": ("evidence_conditional_invariant",),
    }


def test_conditional_status_requires_condition_or_trigger() -> None:
    kwargs = _base_kwargs()
    kwargs["finding_status"] = "CONDITIONAL"

    with pytest.raises(
        ReasoningContractError,
        match="conditional findings and conditional derivations must carry",
    ):
        build_finding(**kwargs)


def test_conditional_derivation_requires_condition_or_trigger() -> None:
    kwargs = _base_kwargs()
    kwargs["derivation_type"] = "CONDITIONAL_DERIVATION"

    with pytest.raises(
        ReasoningContractError,
        match="conditional findings and conditional derivations must carry",
    ):
        build_finding(**kwargs)


def test_condition_is_promoted_to_trigger_for_conditional_finding() -> None:
    kwargs = _base_kwargs()
    kwargs["finding_status"] = "CONDITIONAL"
    kwargs["derivation_type"] = "CONDITIONAL_DERIVATION"
    kwargs["condition"] = "when the policy-defined trigger applies"

    finding = build_finding(**kwargs)

    assert finding.condition == "when the policy-defined trigger applies"
    assert finding.trigger == "when the policy-defined trigger applies"


def test_explicit_trigger_is_accepted_for_conditional_derivation() -> None:
    kwargs = _base_kwargs()
    kwargs["derivation_type"] = "CONDITIONAL_DERIVATION"
    kwargs["trigger"] = "when a governed eligibility condition is satisfied"

    finding = build_finding(**kwargs)

    assert finding.trigger == "when a governed eligibility condition is satisfied"
    assert finding.condition == "when a governed eligibility condition is satisfied"


def test_nonconditional_findings_do_not_require_trigger() -> None:
    finding = build_finding(**_base_kwargs())

    assert finding.finding_status == "SUPPORTED"
    assert finding.derivation_type == "DIRECT_FACT"
    assert finding.trigger is None
    assert finding.condition is None
