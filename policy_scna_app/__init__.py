"""Thin PolicyScna product application layer.

This package is intentionally outside governed insurance-authority roots. It composes
existing governed capabilities into customer-visible product slices without creating
new insurance facts or authority.
"""

from policy_scna_app.health_customer_v0 import (
    HealthCustomerAnswerResult,
    HealthCustomerRelevanceError,
    ask_health_question,
    ask_health_question_live,
    build_health_gsi_vocabulary,
)

__all__ = [
    "HealthCustomerAnswerResult",
    "HealthCustomerRelevanceError",
    "ask_health_question",
    "ask_health_question_live",
    "build_health_gsi_vocabulary",
]
