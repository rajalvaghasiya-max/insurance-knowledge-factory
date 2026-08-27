"""Executable contract for downstream authority-safety enforcement."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.authority_intent_reconciliation import (
    AuthorityIntentReconciliationOutput,
)
from insurance_intelligence.contracts.decision import DecisionGateInput, DecisionGateOutput

SUPPORTED_CONTRACT_VERSION = "1.0"
ENFORCEMENT_OUTCOMES = frozenset(
    {
        "DELEGATED_TO_DECISION_GATE",
        "ADVISORY_PATH_NOT_AUTHORIZED",
        "AUTHORITY_CLARIFICATION_REQUIRED",
        "RECONCILIATION_CLARIFICATION_REQUIRED",
        "INTENT_EXIT_REQUIRED",
        "OUT_OF_SCOPE",
    }
)


class AuthorityEnforcementContractError(ValueError):
    """Raised when authority-enforcement contracts are invalid."""


@dataclass(frozen=True)
class AuthorityEnforcedDecisionInput:
    contract_version: str
    request_id: str
    reconciliation: AuthorityIntentReconciliationOutput
    decision_gate_input: DecisionGateInput


@dataclass(frozen=True)
class AuthorityEnforcementResult:
    contract_version: str
    request_id: str
    enforcement_outcome: str
    minimum_guard: str
    advisory_safety_obligation: bool
    ordinary_assertion_path_permitted: bool
    recommendation_authorized: bool
    decision_gate_called: bool
    decision_output: DecisionGateOutput | None
    clarification_required: bool
    out_of_scope: bool
    basis: str
    enforcement_trace: tuple[str, ...]


def build_input(
    *,
    request_id: str,
    reconciliation: AuthorityIntentReconciliationOutput,
    decision_gate_input: DecisionGateInput,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> AuthorityEnforcedDecisionInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise AuthorityEnforcementContractError("unsupported contract_version")
    if not isinstance(request_id, str) or not request_id.strip():
        raise AuthorityEnforcementContractError("request_id must be non-empty")
    if not isinstance(reconciliation, AuthorityIntentReconciliationOutput):
        raise AuthorityEnforcementContractError(
            "reconciliation must be AuthorityIntentReconciliationOutput"
        )
    if not isinstance(decision_gate_input, DecisionGateInput):
        raise AuthorityEnforcementContractError(
            "decision_gate_input must be validated DecisionGateInput"
        )
    if reconciliation.request_id != request_id or decision_gate_input.request_id != request_id:
        raise AuthorityEnforcementContractError("request_id must match all inputs")
    if reconciliation.recommendation_authorized is not False:
        raise AuthorityEnforcementContractError(
            "reconciliation may not authorize recommendation"
        )
    return AuthorityEnforcedDecisionInput(
        contract_version=contract_version,
        request_id=request_id,
        reconciliation=reconciliation,
        decision_gate_input=decision_gate_input,
    )


def build_result(
    *,
    request_id: str,
    enforcement_outcome: str,
    minimum_guard: str,
    advisory_safety_obligation: bool,
    ordinary_assertion_path_permitted: bool,
    decision_gate_called: bool,
    decision_output: DecisionGateOutput | None,
    clarification_required: bool,
    out_of_scope: bool,
    basis: str,
    enforcement_trace: tuple[str, ...],
    recommendation_authorized: bool = False,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> AuthorityEnforcementResult:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise AuthorityEnforcementContractError("unsupported contract_version")
    if enforcement_outcome not in ENFORCEMENT_OUTCOMES:
        raise AuthorityEnforcementContractError("unsupported enforcement_outcome")
    for value, label in (
        (advisory_safety_obligation, "advisory_safety_obligation"),
        (ordinary_assertion_path_permitted, "ordinary_assertion_path_permitted"),
        (decision_gate_called, "decision_gate_called"),
        (clarification_required, "clarification_required"),
        (out_of_scope, "out_of_scope"),
    ):
        if not isinstance(value, bool):
            raise AuthorityEnforcementContractError(f"{label} must be boolean")
    if recommendation_authorized is not False:
        raise AuthorityEnforcementContractError(
            "authority enforcement may never authorize recommendation"
        )
    if decision_gate_called != (decision_output is not None):
        raise AuthorityEnforcementContractError(
            "decision_gate_called must match decision_output presence"
        )
    if enforcement_outcome == "DELEGATED_TO_DECISION_GATE" and not decision_gate_called:
        raise AuthorityEnforcementContractError(
            "delegated outcome requires Decision Gate execution"
        )
    if enforcement_outcome != "DELEGATED_TO_DECISION_GATE" and decision_gate_called:
        raise AuthorityEnforcementContractError(
            "preflight exit must not call Decision Gate"
        )
    if ordinary_assertion_path_permitted and advisory_safety_obligation:
        raise AuthorityEnforcementContractError(
            "ordinary assertion path cannot coexist with advisory obligation"
        )
    if enforcement_outcome == "ADVISORY_PATH_NOT_AUTHORIZED" and not advisory_safety_obligation:
        raise AuthorityEnforcementContractError(
            "advisory-path withholding requires advisory safety obligation"
        )
    if enforcement_outcome == "DELEGATED_TO_DECISION_GATE" and not ordinary_assertion_path_permitted:
        raise AuthorityEnforcementContractError(
            "v1 delegates only the ordinary assertive path"
        )
    if not isinstance(basis, str) or not basis.strip():
        raise AuthorityEnforcementContractError("basis must be non-empty")
    if not enforcement_trace or not all(isinstance(item, str) and item.strip() for item in enforcement_trace):
        raise AuthorityEnforcementContractError("enforcement_trace must contain entries")
    return AuthorityEnforcementResult(
        contract_version=contract_version,
        request_id=request_id,
        enforcement_outcome=enforcement_outcome,
        minimum_guard=minimum_guard,
        advisory_safety_obligation=advisory_safety_obligation,
        ordinary_assertion_path_permitted=ordinary_assertion_path_permitted,
        recommendation_authorized=False,
        decision_gate_called=decision_gate_called,
        decision_output=decision_output,
        clarification_required=clarification_required,
        out_of_scope=out_of_scope,
        basis=basis,
        enforcement_trace=enforcement_trace,
    )
