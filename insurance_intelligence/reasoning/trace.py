"""Structured, deterministic audit trace for MO-017 reasoning."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from insurance_intelligence.contracts.reasoning import ReasoningTraceEvent, build_trace_event


@dataclass
class ReasoningTraceBuilder:
    trace_id: str
    _events: list[ReasoningTraceEvent] = field(default_factory=list)

    def add(
        self,
        event_type: str,
        decision: str,
        basis: str,
        *,
        requirement_id: str | None = None,
        rule_id: str | None = None,
        evidence_ids: Sequence[str] = (),
        input_references: Sequence[str] = (),
        output_finding_ids: Sequence[str] = (),
    ) -> ReasoningTraceEvent:
        sequence = len(self._events) + 1
        event = build_trace_event(
            trace_id=self.trace_id,
            sequence=sequence,
            event_type=event_type,
            decision=decision,
            basis=basis,
            order_marker=f"event-{sequence:04d}",
            requirement_id=requirement_id,
            rule_id=rule_id,
            evidence_ids=tuple(evidence_ids),
            input_references=tuple(input_references),
            output_finding_ids=tuple(output_finding_ids),
        )
        self._events.append(event)
        return event

    def build(self) -> tuple[ReasoningTraceEvent, ...]:
        return tuple(self._events)
