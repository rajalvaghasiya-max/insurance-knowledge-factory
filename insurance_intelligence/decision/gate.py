"""Executable deterministic Decision and Safety Gate for MO-018E."""
from __future__ import annotations

import hashlib
import json
from typing import Mapping, Sequence

from insurance_intelligence.contracts.decision import (
    DecisionGateInput,
    DecisionGateOutput,
    build_output,
    build_trace_event,
)
from insurance_intelligence.decision.aggregator import aggregate_decision
from insurance_intelligence.decision.evaluator import evaluate_finding
from insurance_intelligence.decision.registry import SafetyPolicyRegistry


class DecisionSafetyGateError(ValueError):
    """Raised when executable gate inputs are invalid."""


def _stable_id(prefix: str, payload: object) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr)
    return f"{prefix}_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:16]}"


def _requested_operations(data: DecisionGateInput) -> tuple[str, ...]:
    raw = data.decision_context.get("requested_operations", ())
    if isinstance(raw, str):
        raw = (raw,)
    if not isinstance(raw, Sequence):
        raise DecisionSafetyGateError("decision_context.requested_operations must be a sequence")
    return tuple(sorted({str(item) for item in raw}))


def _domain(data: DecisionGateInput) -> str:
    value = str(data.decision_context.get("domain", "health"))
    return value if value in {"health", "motor", "life", "travel", "unknown", "any"} else "unknown"


def _topic(data: DecisionGateInput) -> str:
    explicit = data.decision_context.get("topic")
    if explicit is not None:
        return str(explicit)
    if any("copay" in item.rule_id for item in data.reasoning_output.findings):
        return "conditional_copayment" if data.decision_context.get("case_specific_applicability") else "copay"
    if all(item.finding_type == "DOCUMENTED_FACT" for item in data.reasoning_output.findings):
        return "documented_fact"
    return "coverage"


class _TraceBuilder:
    def __init__(self, trace_id: str) -> None:
        self._trace_id = trace_id
        self._events = []

    def add(
        self,
        event_type: str,
        decision: str,
        basis: str,
        *,
        finding_id: str | None = None,
        policy_id: str | None = None,
        input_references: Sequence[str] = (),
        output_references: Sequence[str] = (),
    ) -> None:
        sequence = len(self._events) + 1
        self._events.append(build_trace_event(
            trace_id=self._trace_id,
            sequence=sequence,
            event_type=event_type,
            decision=decision,
            basis=basis,
            finding_id=finding_id,
            policy_id=policy_id,
            input_references=tuple(input_references),
            output_references=tuple(output_references),
            order_marker=f"{sequence:04d}",
        ))

    def build(self):
        return tuple(self._events)


class DecisionSafetyGate:
    """Evaluate reasoning findings and produce an evidence-locked approval packet."""

    def __init__(self, policy_registry: SafetyPolicyRegistry | None = None) -> None:
        self._registry = policy_registry or SafetyPolicyRegistry()

    def decide(self, data: DecisionGateInput) -> DecisionGateOutput:
        if not isinstance(data, DecisionGateInput):
            raise DecisionSafetyGateError("data must be a validated DecisionGateInput")

        plan = data.reasoning_plan
        evidence = data.evidence_resolution
        reasoning = data.reasoning_output
        operations = _requested_operations(data)
        domain = _domain(data)
        topic = _topic(data)
        context = dict(data.decision_context)
        out_of_scope = plan.plan_status == "OUT_OF_SCOPE" or reasoning.reasoning_status == "OUT_OF_SCOPE"

        decision_id = _stable_id("decision", {
            "request_id": data.request_id,
            "plan_id": plan.plan_id,
            "resolution_id": evidence.resolution_id,
            "reasoning_id": reasoning.reasoning_id,
            "strict_mode": data.strict_mode,
            "context": sorted((str(k), repr(v)) for k, v in context.items()),
        })
        trace = _TraceBuilder(_stable_id("trace", decision_id))
        trace.add("DECISION_STARTED", "STARTED", "validated cross-stage inputs received", input_references=(plan.plan_id, evidence.resolution_id, reasoning.reasoning_id))
        trace.add("INPUT_VALIDATED", "VALID", "request identifiers and governed stage outputs are aligned", input_references=(data.request_id,))

        evaluations = []
        for finding in sorted(reasoning.findings, key=lambda item: item.finding_id):
            trace.add("FINDING_RECEIVED", "RECEIVED", "structured reasoning finding received for safety evaluation", finding_id=finding.finding_id, input_references=finding.evidence_ids)
            evaluated = evaluate_finding(
                finding=finding,
                evidence_resolution=evidence,
                reasoning_output=reasoning,
                policy_registry=self._registry,
                domain=domain,
                topic=topic,
                decision_context=context,
                strict_mode=data.strict_mode,
                requested_operations=operations,
            )
            evaluations.append(evaluated)
            for policy_id in evaluated.matched_policy_ids:
                trace.add("SAFETY_POLICY_EVALUATED", "MATCHED", "deterministic safety policy matched", finding_id=finding.finding_id, policy_id=policy_id)
            for issue in evaluated.safety_issues:
                trace.add("SAFETY_ISSUE_RECORDED", issue.status, issue.description, finding_id=finding.finding_id, policy_id=issue.policy_id, input_references=issue.evidence_ids, output_references=(issue.issue_id,))
            for clarification in evaluated.clarifications:
                trace.add("CLARIFICATION_REQUIRED", "REQUIRED", clarification.reason, finding_id=finding.finding_id, output_references=(clarification.clarification_id,))
            disposition = evaluated.finding_disposition
            if disposition.disposition in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
                trace.add("FINDING_APPROVED", disposition.disposition, disposition.basis, finding_id=finding.finding_id, input_references=disposition.approved_evidence_ids)
            else:
                trace.add("FINDING_WITHHELD", disposition.disposition, disposition.basis, finding_id=finding.finding_id, output_references=disposition.safety_issue_ids)

        aggregate = aggregate_decision(
            request_id=data.request_id,
            evaluations=tuple(evaluations),
            prohibited_operations=operations,
            out_of_scope=out_of_scope,
        )
        if aggregate.decision == "HUMAN_REVIEW_REQUIRED":
            trace.add("HUMAN_REVIEW_REQUIRED", aggregate.decision, "; ".join(aggregate.human_review_reasons))
        if aggregate.response_packet is not None:
            trace.add("RESPONSE_PACKET_ASSEMBLED", aggregate.decision, "evidence-locked approved response packet assembled", input_references=aggregate.response_packet.approved_finding_ids, output_references=(aggregate.response_packet.packet_id,))
        trace.add("DECISION_COMPLETED", aggregate.decision, "deterministic safety-gate aggregation completed")

        return build_output(
            request_id=data.request_id,
            decision_id=decision_id,
            decision=aggregate.decision,
            finding_dispositions=aggregate.finding_dispositions,
            safety_issues=aggregate.safety_issues,
            clarifications=aggregate.clarifications,
            response_packet=aggregate.response_packet,
            blocked_content=aggregate.blocked_content,
            limitations=aggregate.limitations,
            human_review_reasons=aggregate.human_review_reasons,
            confidence=aggregate.confidence,
            decision_trace=trace.build(),
        )
