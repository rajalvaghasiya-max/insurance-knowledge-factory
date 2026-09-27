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


_HUMAN_MEANING_SECTION_TYPES = frozenset(
    {"EDUCATION", "CUSTOMER_EXPLANATION", "EXAMPLE", "PRACTICAL_ILLUSTRATION"}
)
_ANSWER_STATUSES = frozenset({"ANSWER", "ANSWER_WITH_LIMITATIONS"})
_NON_ANSWER_MESSAGES = {
    "INSUFFICIENT_EVIDENCE": "I cannot determine this safely because the required evidence is incomplete.",
    "CONFLICTING_EVIDENCE": "I cannot determine this safely because the governed evidence is conflicting.",
    "UNSUPPORTED": "I cannot determine this safely from the governed information available.",
    "BLOCKED": "I cannot provide a supported answer through this path.",
    "OUT_OF_SCOPE": "This request is outside the supported answer scope.",
}
_SUPPORTED_STATUSES = frozenset((*_ANSWER_STATUSES, *_NON_ANSWER_MESSAGES))


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
    diagnostic_limitations: tuple[str, ...] = ()


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


def _included_customer_qualifications(response: ResponseAssemblerOutput) -> tuple[str, ...]:
    return tuple(
        section.text
        for section in response.sections
        if section.status == "INCLUDED" and section.section_type == "CUSTOMER_QUALIFICATION"
    )


def _included_next_steps(response: ResponseAssemblerOutput) -> tuple[str, ...]:
    return tuple(
        section.text
        for section in response.sections
        if section.status == "INCLUDED" and section.section_type == "NEXT_STEP"
    )


def _unknowns(response: ResponseAssemblerOutput) -> tuple[str, ...]:
    typed = _included_customer_qualifications(response)
    if typed:
        return typed
    if response.customer_reason is not None:
        return (response.customer_reason.text,)
    return ()


def _resolution_next_step(response: ResponseAssemblerOutput, unknowns: tuple[str, ...]) -> str | None:
    typed = tuple(dict.fromkeys(_included_next_steps(response)))
    if typed:
        return " ".join(typed)
    if response.customer_reason is not None:
        if response.customer_reason.resolving_requirement is not None:
            return response.customer_reason.resolving_requirement
        if response.customer_reason.reason_kind == "SOURCE_DOES_NOT_ESTABLISH":
            return (
                "Check the governing policy wording or confirm the unresolved rule with the insurer "
                "or advisor before relying on a conclusion."
            )
        return (
            "Check the governing policy documents or confirm the unresolved point with the insurer "
            "or advisor before relying on a conclusion."
        )
    if not unknowns:
        return None
    if response.response_status not in {"ANSWER_WITH_LIMITATIONS", *_NON_ANSWER_MESSAGES}:
        return None
    return (
        "Resolve the uncertainty stated above by checking the governing policy documents or "
        "confirming it with the insurer or advisor before relying on a conclusion."
    )


def project_human_answer(response: ResponseAssemblerOutput) -> HumanAnswerProjection:
    """Project one generic human answer and a separate provenance panel.

    This function never chooses wording by insurer, product, topic, or rule ID. It copies
    approved human-facing text from answer responses. For canonical fail-closed statuses it
    adds only generic status wording plus workflow guidance; it never converts a withheld
    insurance conclusion into an answer.
    """
    if not isinstance(response, ResponseAssemblerOutput):
        raise HumanAnswerProjectionError("response must be a ResponseAssemblerOutput")
    if response.response_status not in _SUPPORTED_STATUSES:
        raise HumanAnswerProjectionError(
            f"D0 human projection does not support response status {response.response_status!r}"
        )
    if response.response_status in _ANSWER_STATUSES:
        if not response.direct_answer:
            raise HumanAnswerProjectionError("answer response must contain a direct_answer")
        answer = response.direct_answer
    else:
        if response.direct_answer is not None:
            raise HumanAnswerProjectionError("fail-closed response must not contain direct_answer")
        answer = _NON_ANSWER_MESSAGES[response.response_status]

    meaning = _included_meaning(response)
    unknowns = _unknowns(response)
    human = HumanAnswerView(
        answer=answer,
        meaning=meaning,
        unknowns=unknowns,
        next_step=_resolution_next_step(response, unknowns),
    )
    provenance = ProvenancePanel(
        response_id=response.response_id,
        response_section_ids=tuple(section.section_id for section in response.sections),
        evidence_references=tuple(response.evidence_references),
        response_trace=tuple(response.response_trace),
        diagnostic_limitations=tuple(response.limitations),
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
