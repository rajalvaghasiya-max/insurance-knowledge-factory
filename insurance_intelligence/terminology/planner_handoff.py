"""Safe terminology-to-planner handoff contract for MO-024D.

This module converts canonical concept resolution into a planning hint only. It
never retrieves evidence, evaluates product applicability, executes reasoning,
or claims that a downstream capability exists. Capability eligibility remains a
planner / registry responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from insurance_intelligence.terminology.concept_resolver import (
    CanonicalConceptResolution,
)

HANDOFF_STATUSES = frozenset({"READY", "BLOCKED", "INVALID_INPUT"})


@dataclass(frozen=True)
class TerminologyPlannerHandoff:
    handoff_id: str
    resolution_id: str
    status: str
    concept_id: str | None
    domain: str | None
    downstream_topic: str | None
    candidate_concept_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in HANDOFF_STATUSES:
            raise ValueError(f"unsupported handoff status: {self.status!r}")
        if not self.reason_codes:
            raise ValueError("reason_codes must not be empty")
        if self.status == "READY":
            if not self.concept_id or not self.domain or not self.downstream_topic:
                raise ValueError("READY handoff requires concept, domain, and downstream topic")
            if self.candidate_concept_ids != (self.concept_id,):
                raise ValueError("READY handoff must preserve exactly the selected concept")
        else:
            if any(value is not None for value in (self.concept_id, self.downstream_topic)):
                raise ValueError(f"{self.status} handoff cannot publish a selected planning target")


def _stable_id(*parts: object) -> str:
    payload = "\x1f".join("" if part is None else str(part) for part in parts)
    return f"terminology_handoff_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def build_planner_handoff(resolution: object) -> TerminologyPlannerHandoff:
    """Convert a canonical terminology resolution into a safe planner hint.

    READY means only that terminology resolution produced one governed canonical
    concept with a declared downstream topic. It does not mean a reasoning rule,
    product implementation, or evidence source is available.
    """
    if not isinstance(resolution, CanonicalConceptResolution):
        return TerminologyPlannerHandoff(
            handoff_id=_stable_id("INVALID_INPUT", repr(resolution)),
            resolution_id="invalid-resolution",
            status="INVALID_INPUT",
            concept_id=None,
            domain=None,
            downstream_topic=None,
            candidate_concept_ids=(),
            reason_codes=("INVALID_TERMINOLOGY_RESOLUTION",),
        )

    candidate_ids = tuple(item.concept_id for item in resolution.candidates)

    if resolution.status != "RESOLVED":
        reason = {
            "AMBIGUOUS": "TERMINOLOGY_AMBIGUOUS",
            "NOT_RESOLVED": "TERMINOLOGY_NOT_RESOLVED",
            "INVALID_INPUT": "TERMINOLOGY_INVALID_INPUT",
        }.get(resolution.status, "TERMINOLOGY_NOT_READY")
        return TerminologyPlannerHandoff(
            handoff_id=_stable_id("BLOCKED", resolution.resolution_id, reason, *candidate_ids),
            resolution_id=resolution.resolution_id,
            status="BLOCKED",
            concept_id=None,
            domain=resolution.domain,
            downstream_topic=None,
            candidate_concept_ids=candidate_ids,
            reason_codes=(reason,),
        )

    selected = resolution.selected_concept
    if selected is None:
        return TerminologyPlannerHandoff(
            handoff_id=_stable_id("BLOCKED", resolution.resolution_id, "MISSING_SELECTED_CONCEPT"),
            resolution_id=resolution.resolution_id,
            status="BLOCKED",
            concept_id=None,
            domain=resolution.domain,
            downstream_topic=None,
            candidate_concept_ids=(),
            reason_codes=("MISSING_SELECTED_CONCEPT",),
        )

    if selected.downstream_topic is None:
        return TerminologyPlannerHandoff(
            handoff_id=_stable_id("BLOCKED", resolution.resolution_id, selected.concept_id, "MISSING_DOWNSTREAM_TOPIC"),
            resolution_id=resolution.resolution_id,
            status="BLOCKED",
            concept_id=None,
            domain=selected.domain,
            downstream_topic=None,
            candidate_concept_ids=(selected.concept_id,),
            reason_codes=("MISSING_DOWNSTREAM_TOPIC",),
        )

    return TerminologyPlannerHandoff(
        handoff_id=_stable_id(
            "READY",
            resolution.resolution_id,
            selected.concept_id,
            selected.domain,
            selected.downstream_topic,
        ),
        resolution_id=resolution.resolution_id,
        status="READY",
        concept_id=selected.concept_id,
        domain=selected.domain,
        downstream_topic=selected.downstream_topic,
        candidate_concept_ids=(selected.concept_id,),
        reason_codes=("CANONICAL_CONCEPT_READY_FOR_PLANNING",),
    )
