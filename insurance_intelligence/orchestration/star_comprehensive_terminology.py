"""Controlled Star Comprehensive terminology orchestration wiring for MO-024G."""
from __future__ import annotations

from insurance_intelligence.orchestration.terminology_gate import (
    TerminologyOrchestrationGate,
)
from insurance_intelligence.terminology.context_resolver import (
    ContextualTerminologyResolver,
)
from insurance_intelligence.terminology.star_comprehensive_aliases import (
    build_star_comprehensive_alias_resolver,
)


def build_star_comprehensive_terminology_gate() -> TerminologyOrchestrationGate:
    """Return the governed Star Comprehensive terminology pre-reasoning gate."""
    return TerminologyOrchestrationGate(
        resolver=ContextualTerminologyResolver(
            resolver=build_star_comprehensive_alias_resolver()
        )
    )


__all__ = ["build_star_comprehensive_terminology_gate"]
