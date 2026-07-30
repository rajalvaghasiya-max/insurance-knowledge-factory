"""Fail-closed terminology enrichment gate for MO-024G.

The gate runs before reasoning-plan construction. It exposes governed canonical
terminology and product implementation context only after deterministic contextual
resolution. Unresolved terminology produces a blocked handoff and cannot silently
advance to explanation, ranking, suitability, recommendation, or claim logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Mapping

from insurance_intelligence.terminology.context_resolver import (
    ContextualTerminologyResolver,
    TerminologyContextQuery,
)


class TerminologyOrchestrationError(ValueError):
    """Raised when a terminology orchestration request is structurally invalid."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TerminologyOrchestrationError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class TerminologyOrchestrationRequest:
    """Terminology text and product context supplied before reasoning planning."""

    request_id: str
    text: str
    insurer_id: str | None = None
    product_id: str | None = None
    product_variant_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _required_text(self.request_id, "request_id"))
        object.__setattr__(self, "text", _required_text(self.text, "text"))


@dataclass(frozen=True)
class TerminologyOrchestrationResult:
    """A ready enrichment payload or an explicit blocked orchestration handoff."""

    request_id: str
    status: str
    canonical_context: Mapping[str, object]
    reason_codes: tuple[str, ...] = ()
    missing_context: tuple[str, ...] = ()
    candidate_term_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _required_text(self.request_id, "request_id"))
        if self.status not in {"READY", "BLOCKED"}:
            raise TerminologyOrchestrationError("status must be READY or BLOCKED")
        object.__setattr__(self, "canonical_context", MappingProxyType(dict(self.canonical_context)))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "missing_context", tuple(self.missing_context))
        object.__setattr__(self, "candidate_term_ids", tuple(self.candidate_term_ids))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        if self.status == "READY":
            if self.reason_codes or self.missing_context:
                raise TerminologyOrchestrationError(
                    "READY results cannot contain unresolved reason codes or missing context"
                )
            required = {
                "terminology_term_id",
                "terminology_display_name",
                "canonical_concept_family_id",
                "canonical_concept_name",
                "product_term_implementation_id",
                "behaviour_signature_id",
                "terminology_relationship",
            }
            missing = required.difference(self.canonical_context)
            if missing:
                raise TerminologyOrchestrationError(
                    f"READY canonical_context is missing required keys: {sorted(missing)}"
                )
        elif not self.reason_codes:
            raise TerminologyOrchestrationError("BLOCKED results must contain reason_codes")

    @property
    def may_advance(self) -> bool:
        return self.status == "READY"


@dataclass(frozen=True)
class TerminologyOrchestrationGate:
    """Resolve terminology and produce a bounded downstream context handoff."""

    resolver: ContextualTerminologyResolver

    def evaluate(
        self,
        request: TerminologyOrchestrationRequest,
        *,
        as_of: date,
    ) -> TerminologyOrchestrationResult:
        contextual = self.resolver.resolve(
            TerminologyContextQuery(
                text=request.text,
                insurer_id=request.insurer_id,
                product_id=request.product_id,
                product_variant_id=request.product_variant_id,
            ),
            as_of=as_of,
        )
        if not contextual.is_resolved:
            return TerminologyOrchestrationResult(
                request_id=request.request_id,
                status="BLOCKED",
                canonical_context={},
                reason_codes=contextual.reason_codes,
                missing_context=contextual.missing_context,
                candidate_term_ids=contextual.candidate_term_ids,
                warnings=(
                    "Terminology resolution did not produce one governed product-scoped concept; downstream reasoning and explanation must not proceed.",
                ),
            )

        result = contextual.result
        assert result is not None
        assert result.selected_concept is not None
        assert result.implementation is not None
        canonical_context = {
            "terminology_term_id": result.term.term_id,
            "terminology_display_name": result.term.display_name,
            "canonical_concept_family_id": result.selected_concept.concept_family_id,
            "canonical_concept_name": result.selected_concept.canonical_name,
            "canonical_concept_definition": result.selected_concept.definition,
            "product_term_implementation_id": result.implementation.implementation_id,
            "behaviour_signature_id": result.implementation.behaviour_signature_id,
            "terminology_conditions": result.implementation.conditions,
            "terminology_limitations": result.implementation.limitations,
            "terminology_relationship": result.relationship.value,
            "terminology_resolution_id": result.resolution_id,
            "terminology_review_status": result.review_status.value,
            "terminology_publication_status": result.publication_status.value,
        }
        return TerminologyOrchestrationResult(
            request_id=request.request_id,
            status="READY",
            canonical_context=canonical_context,
        )


__all__ = [
    "TerminologyOrchestrationError",
    "TerminologyOrchestrationGate",
    "TerminologyOrchestrationRequest",
    "TerminologyOrchestrationResult",
]
