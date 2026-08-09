"""Intent and personalization context boundary for MO-027A.

This module governs whether customer-specific context may participate in a turn.
It deliberately does not classify free-form language, infer health facts, rank
products, or recommend a product. Upstream understanding may propose an intent;
this boundary decides what context is admissible for downstream reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PersonalizationBoundaryError(ValueError):
    """Raised when a personalization-context transition violates an invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonalizationBoundaryError(f"{field_name} must be non-empty text")
    return value.strip()


class TurnIntent(str, Enum):
    PRODUCT_ONLY = "PRODUCT_ONLY"
    PERSONALIZED_DECISION_SUPPORT = "PERSONALIZED_DECISION_SUPPORT"
    PERSONALIZED_IMPLICATION = "PERSONALIZED_IMPLICATION"


class PersonalizationState(str, Enum):
    PRODUCT_ONLY = "PRODUCT_ONLY"
    PERSONALIZED_ACTIVE = "PERSONALIZED_ACTIVE"


class ContextTransition(str, Enum):
    STAY_PRODUCT_ONLY = "STAY_PRODUCT_ONLY"
    ENTER_PERSONALIZED = "ENTER_PERSONALIZED"
    CONTINUE_PERSONALIZED = "CONTINUE_PERSONALIZED"
    EXIT_TO_PRODUCT_ONLY = "EXIT_TO_PRODUCT_ONLY"


class CustomerContextAccess(str, Enum):
    PROHIBITED = "PROHIBITED"
    PERMITTED = "PERMITTED"


@dataclass(frozen=True)
class PersonalizationBoundaryState:
    state_id: str
    state: PersonalizationState
    active_customer_context_id: str | None = None
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_id", _required_text(self.state_id, "state_id"))
        object.__setattr__(
            self,
            "contract_version",
            _required_text(self.contract_version, "contract_version"),
        )
        if not isinstance(self.state, PersonalizationState):
            raise PersonalizationBoundaryError("state must be a PersonalizationState")
        if self.state is PersonalizationState.PRODUCT_ONLY:
            if self.active_customer_context_id is not None:
                raise PersonalizationBoundaryError(
                    "PRODUCT_ONLY state cannot carry an active customer context"
                )
        else:
            object.__setattr__(
                self,
                "active_customer_context_id",
                _required_text(
                    self.active_customer_context_id,  # type: ignore[arg-type]
                    "active_customer_context_id",
                ),
            )


@dataclass(frozen=True)
class PersonalizationBoundaryDecision:
    decision_id: str
    prior_state: PersonalizationState
    intent: TurnIntent
    transition: ContextTransition
    next_state: PersonalizationState
    customer_context_access: CustomerContextAccess
    active_customer_context_id: str | None
    reason: str
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in ("decision_id", "reason", "contract_version"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.prior_state, PersonalizationState):
            raise PersonalizationBoundaryError("prior_state must be a PersonalizationState")
        if not isinstance(self.intent, TurnIntent):
            raise PersonalizationBoundaryError("intent must be a TurnIntent")
        if not isinstance(self.transition, ContextTransition):
            raise PersonalizationBoundaryError("transition must be a ContextTransition")
        if not isinstance(self.next_state, PersonalizationState):
            raise PersonalizationBoundaryError("next_state must be a PersonalizationState")
        if not isinstance(self.customer_context_access, CustomerContextAccess):
            raise PersonalizationBoundaryError(
                "customer_context_access must be a CustomerContextAccess"
            )
        if self.customer_context_access is CustomerContextAccess.PROHIBITED:
            if self.active_customer_context_id is not None:
                raise PersonalizationBoundaryError(
                    "PROHIBITED customer-context access cannot carry a context id"
                )
        else:
            object.__setattr__(
                self,
                "active_customer_context_id",
                _required_text(
                    self.active_customer_context_id,  # type: ignore[arg-type]
                    "active_customer_context_id",
                ),
            )


def decide_personalization_boundary(
    *,
    decision_id: str,
    prior: PersonalizationBoundaryState,
    intent: TurnIntent,
    customer_context_id: str | None = None,
) -> PersonalizationBoundaryDecision:
    """Apply explicit context-isolation rules for one turn.

    PRODUCT_ONLY always prohibits customer-context access, even when the previous
    turn was personalized. Personalized intents require an explicit context id on
    entry and reuse the active context only while personalization remains active.
    """

    if type(prior) is not PersonalizationBoundaryState:
        raise PersonalizationBoundaryError(
            "prior must be the exact PersonalizationBoundaryState type"
        )
    if not isinstance(intent, TurnIntent):
        raise PersonalizationBoundaryError("intent must be a TurnIntent")

    if intent is TurnIntent.PRODUCT_ONLY:
        transition = (
            ContextTransition.EXIT_TO_PRODUCT_ONLY
            if prior.state is PersonalizationState.PERSONALIZED_ACTIVE
            else ContextTransition.STAY_PRODUCT_ONLY
        )
        return PersonalizationBoundaryDecision(
            decision_id=decision_id,
            prior_state=prior.state,
            intent=intent,
            transition=transition,
            next_state=PersonalizationState.PRODUCT_ONLY,
            customer_context_access=CustomerContextAccess.PROHIBITED,
            active_customer_context_id=None,
            reason=(
                "Product-only reasoning must not consume customer-specific context, "
                "including context accumulated in earlier personalized turns."
            ),
        )

    if prior.state is PersonalizationState.PRODUCT_ONLY:
        context_id = _required_text(customer_context_id, "customer_context_id")  # type: ignore[arg-type]
        return PersonalizationBoundaryDecision(
            decision_id=decision_id,
            prior_state=prior.state,
            intent=intent,
            transition=ContextTransition.ENTER_PERSONALIZED,
            next_state=PersonalizationState.PERSONALIZED_ACTIVE,
            customer_context_access=CustomerContextAccess.PERMITTED,
            active_customer_context_id=context_id,
            reason=(
                "The current turn explicitly requests personalized reasoning and is "
                "bound to the supplied customer decision context."
            ),
        )

    active_id = prior.active_customer_context_id
    assert active_id is not None
    if customer_context_id is not None and customer_context_id.strip() != active_id:
        raise PersonalizationBoundaryError(
            "cannot silently replace the active customer context during a personalized turn"
        )
    return PersonalizationBoundaryDecision(
        decision_id=decision_id,
        prior_state=prior.state,
        intent=intent,
        transition=ContextTransition.CONTINUE_PERSONALIZED,
        next_state=PersonalizationState.PERSONALIZED_ACTIVE,
        customer_context_access=CustomerContextAccess.PERMITTED,
        active_customer_context_id=active_id,
        reason=(
            "Personalized reasoning remains active for the same explicitly bound "
            "customer decision context."
        ),
    )


def next_boundary_state(
    decision: PersonalizationBoundaryDecision,
) -> PersonalizationBoundaryState:
    if type(decision) is not PersonalizationBoundaryDecision:
        raise PersonalizationBoundaryError(
            "decision must be the exact PersonalizationBoundaryDecision type"
        )
    return PersonalizationBoundaryState(
        state_id=f"state_after:{decision.decision_id}",
        state=decision.next_state,
        active_customer_context_id=decision.active_customer_context_id,
    )


__all__ = [
    "ContextTransition",
    "CustomerContextAccess",
    "PersonalizationBoundaryDecision",
    "PersonalizationBoundaryError",
    "PersonalizationBoundaryState",
    "PersonalizationState",
    "TurnIntent",
    "decide_personalization_boundary",
    "next_boundary_state",
]
