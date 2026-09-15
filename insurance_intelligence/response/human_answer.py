"""Deterministic human-view projection over canonical assembled responses.

The projector is presentation-only. It consumes a validated ResponseAssemblerOutput,
preserves the approved answer/meaning/limitations without adding insurance facts, and
keeps provenance in a separate developer-facing panel.
"""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.response import (
    EvidenceReference,
    ResponseAssemblerOutput,
    ResponseTraceEvent,
)


class HumanAnswerProjectionError(ValueError):
    """Raised when an assembled response cannot be projected safely."""


_HUMAN_MEANING_SECTION_TYPES = frozenset({"EXPLANATION", "CONDITION", "IMPACT"})
_ANSWER_STATUSES = frozenset({"ANSWER", "ANSWER_WITH_LIMITATIONS"})


@dataclass(frozen=True)
class HumanAnswerView:
    """Human-facing answer only; no evidence IDs or machine trace objects."""

    answer: str
    meaning: tuple[str, ...]
    unknowns: tuple[str, ...]
    next_step: str | None


@dataclass(frozen=True)
class ProvenancePanel:
    """Developer/audit view kept separate from the human answer."""

    response_id: str
    response_section_ids: tuple[str, ...]
    evidence_references: tuple[EvidenceReference, ...]
    response_trace: tuple[ResponseTraceEvent, ...]


@dataclass(frozen=True)
class HumanAnswerProjection:
    source_response_id: str
    human_view: HumanAnswerView
    provenance_panel: ProvenancePanel


def _included_meaning(response: ResponseAssemblerOutput) -> tuple[str, ...]:
    return tuple(
        section.text
        for section in response.sections
        if section.status == "INCLUDED" and section.section_type in _HUMAN_MEANING_SECTION_TYPES
    )


def _unknowns(response: ResponseAssemblerOutput) -> tuple[str, ...]:
    # Limitations are already evidence/decision-governed upstream. Preserve exact text.
    return tuple(response.limitations)


def _resolution_next_step(response: ResponseAssemblerOutput, unknowns: tuple[str, ...]) -> str | None:
    if response.response_status != "ANSWER_WITH_LIMITATIONS" or not unknowns:
        return None
    return (
        "Before relying on this answer, resolve the uncertainty stated above by checking the "
        "governing policy documents or confirming it with the insurer or advisor."
    )


def project_human_answer(response: ResponseAssemblerOutput) -> HumanAnswerProjection:
    """Project one generic human answer and a separate provenance panel.

    This function never chooses wording by insurer, product, topic, or rule ID. It copies
    approved human-facing text from the canonical response and adds only generic workflow
    guidance for resolving an already-stated uncertainty.
    """
    if not isinstance(response, ResponseAssemblerOutput):
        raise HumanAnswerProjectionError("response must be a ResponseAssemblerOutput")
    if response.response_status not in _ANSWER_STATUSES:
        raise HumanAnswerProjectionError(
            f"D0 human projection supports answer statuses only; got {response.response_status!r}"
        )
    if not response.direct_answer:
        raise HumanAnswerProjectionError("answer response must contain a direct_answer")

    meaning = _included_meaning(response)
    unknowns = _unknowns(response)
    human = HumanAnswerView(
        answer=response.direct_answer,
        meaning=meaning,
        unknowns=unknowns,
        next_step=_resolution_next_step(response, unknowns),
    )
    provenance = ProvenancePanel(
        response_id=response.response_id,
        response_section_ids=tuple(section.section_id for section in response.sections),
        evidence_references=tuple(response.evidence_references),
        response_trace=tuple(response.response_trace),
    )
    return HumanAnswerProjection(
        source_response_id=response.response_id,
        human_view=human,
        provenance_panel=provenance,
    )


__all__ = [
    "HumanAnswerProjection",
    "HumanAnswerProjectionError",
    "HumanAnswerView",
    "ProvenancePanel",
    "project_human_answer",
]
