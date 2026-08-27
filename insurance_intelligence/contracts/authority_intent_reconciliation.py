"""Executable contract for authority × intent reconciliation."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.intent import IntentAnalyzerOutput
from insurance_intelligence.contracts.request_authority import RequestAuthorityOutput

SUPPORTED_CONTRACT_VERSION = "1.0"
RECONCILIATION_STATUSES = frozenset(
    {
        "CONSISTENT_ASSERTIVE",
        "CONSISTENT_ADVISORY",
        "CONSISTENT_MIXED",
        "AUTHORITY_STRICTER_THAN_INTENT",
        "INTENT_RAISES_TO_ADVISORY",
        "AUTHORITY_UNRESOLVED",
        "INTENT_EXIT_REQUIRED",
        "OUT_OF_SCOPE",
    }
)
MINIMUM_GUARDS = frozenset(
    {
        "STANDARD_ASSERTION_GROUNDING",
        "ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
        "SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED",
        "ADVISORY_HOLD_AND_CLARIFY_AUTHORITY",
        "INTENT_EXIT_BEFORE_REASONING",
        "OUT_OF_SCOPE_EXIT",
    }
)


class AuthorityIntentReconciliationError(ValueError):
    """Raised when authority/intent reconciliation input or output is invalid."""


@dataclass(frozen=True)
class AuthorityIntentReconciliationInput:
    contract_version: str
    request_id: str
    authority: RequestAuthorityOutput
    intent: IntentAnalyzerOutput


@dataclass(frozen=True)
class AuthorityIntentReconciliationOutput:
    contract_version: str
    request_id: str
    authority_class: str
    primary_intent: str
    secondary_intents: tuple[str, ...]
    reconciliation_status: str
    minimum_guard: str
    advisory_safety_obligation: bool
    authority_clarification_required: bool
    reconciliation_clarification_required: bool
    intent_exit_required: bool
    ordinary_assertion_path_permitted: bool
    recommendation_authorized: bool
    basis: str


def build_input(
    *,
    request_id: str,
    authority: RequestAuthorityOutput,
    intent: IntentAnalyzerOutput,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> AuthorityIntentReconciliationInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise AuthorityIntentReconciliationError("unsupported contract_version")
    if not isinstance(request_id, str) or not request_id.strip():
        raise AuthorityIntentReconciliationError("request_id must be non-empty")
    if not isinstance(authority, RequestAuthorityOutput):
        raise AuthorityIntentReconciliationError("authority must be RequestAuthorityOutput")
    if not isinstance(intent, IntentAnalyzerOutput):
        raise AuthorityIntentReconciliationError("intent must be IntentAnalyzerOutput")
    if authority.request_id != request_id or intent.request_id != request_id:
        raise AuthorityIntentReconciliationError("request_id must match authority and intent outputs")
    return AuthorityIntentReconciliationInput(
        contract_version=contract_version,
        request_id=request_id,
        authority=authority,
        intent=intent,
    )


def build_output(
    *,
    request_id: str,
    authority_class: str,
    primary_intent: str,
    secondary_intents: tuple[str, ...],
    reconciliation_status: str,
    minimum_guard: str,
    advisory_safety_obligation: bool,
    authority_clarification_required: bool,
    reconciliation_clarification_required: bool,
    intent_exit_required: bool,
    ordinary_assertion_path_permitted: bool,
    basis: str,
    recommendation_authorized: bool = False,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> AuthorityIntentReconciliationOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise AuthorityIntentReconciliationError("unsupported contract_version")
    if reconciliation_status not in RECONCILIATION_STATUSES:
        raise AuthorityIntentReconciliationError("unsupported reconciliation_status")
    if minimum_guard not in MINIMUM_GUARDS:
        raise AuthorityIntentReconciliationError("unsupported minimum_guard")
    for value, label in (
        (advisory_safety_obligation, "advisory_safety_obligation"),
        (authority_clarification_required, "authority_clarification_required"),
        (reconciliation_clarification_required, "reconciliation_clarification_required"),
        (intent_exit_required, "intent_exit_required"),
        (ordinary_assertion_path_permitted, "ordinary_assertion_path_permitted"),
    ):
        if not isinstance(value, bool):
            raise AuthorityIntentReconciliationError(f"{label} must be boolean")
    if recommendation_authorized is not False:
        raise AuthorityIntentReconciliationError("reconciliation may never authorize recommendation")
    if ordinary_assertion_path_permitted and (
        advisory_safety_obligation
        or authority_clarification_required
        or reconciliation_clarification_required
        or intent_exit_required
    ):
        raise AuthorityIntentReconciliationError(
            "ordinary assertion path cannot bypass advisory/clarification/exit obligations"
        )
    if authority_class == "UNRESOLVED" and not advisory_safety_obligation:
        raise AuthorityIntentReconciliationError("UNRESOLVED authority must retain advisory safety")
    if minimum_guard == "STANDARD_ASSERTION_GROUNDING" and not ordinary_assertion_path_permitted:
        raise AuthorityIntentReconciliationError("standard assertion guard requires permitted assertion path")
    if not isinstance(basis, str) or not basis.strip():
        raise AuthorityIntentReconciliationError("basis must be non-empty")
    return AuthorityIntentReconciliationOutput(
        contract_version=contract_version,
        request_id=request_id,
        authority_class=authority_class,
        primary_intent=primary_intent,
        secondary_intents=secondary_intents,
        reconciliation_status=reconciliation_status,
        minimum_guard=minimum_guard,
        advisory_safety_obligation=advisory_safety_obligation,
        authority_clarification_required=authority_clarification_required,
        reconciliation_clarification_required=reconciliation_clarification_required,
        intent_exit_required=intent_exit_required,
        ordinary_assertion_path_permitted=ordinary_assertion_path_permitted,
        recommendation_authorized=False,
        basis=basis,
    )
