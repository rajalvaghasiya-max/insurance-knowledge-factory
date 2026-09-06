"""Generic extension of the proven real response path through authority-enforced decision.

This module composes the existing real reasoning path with the existing
AuthorityEnforcedDecisionGate. It does not alter reconciliation, reasoning, decision,
or safety semantics and intentionally stops at DECISION_GATE_AUTHORITY_ENFORCED.
"""
from __future__ import annotations

from dataclasses import asdict

from insurance_intelligence.authority_enforced_decision_gate import AuthorityEnforcedDecisionGate
from insurance_intelligence.contracts.authority_enforcement import (
    AuthorityEnforcementResult,
    build_input as build_authority_enforced_decision_input,
)
from insurance_intelligence.contracts.authority_intent_reconciliation import (
    AuthorityIntentReconciliationOutput,
)
from insurance_intelligence.contracts.decision import build_input as build_decision_input
from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.reasoning import ReasoningEngineOutput
from insurance_intelligence.contracts.reasoning_plan import ReasoningPlan
from insurance_intelligence.orchestration.intelligence_adapters import (
    build_intelligence_stage_adapter,
    build_raw_intelligence_stage_output,
)
from insurance_intelligence.orchestration.real_response_prefix import (
    RealResponsePrefixDependencies,
    RealResponsePrefixError,
)
from insurance_intelligence.orchestration.real_response_reasoning import (
    build_real_response_reasoning_adapters,
)


def _output_id(execution_id: str, stage: str) -> str:
    return f"{execution_id}:real:{stage.lower()}"


def build_real_response_decision_adapters(*, dependencies: RealResponsePrefixDependencies):
    """Build the proven real path plus canonical authority-enforced decision."""
    prior = build_real_response_reasoning_adapters(dependencies=dependencies)

    def decision(*, request, stage, input_ids, knowledge_snapshot_id):
        if stage != "DECISION_GATE_AUTHORITY_ENFORCED":
            raise RealResponsePrefixError("decision stage mismatch")
        reconciliation = dependencies.store.get(
            _output_id(request.execution_id, "AUTHORITY_INTENT_RECONCILIATION"),
            expected_type=AuthorityIntentReconciliationOutput,
        )
        plan = dependencies.store.get(
            _output_id(request.execution_id, "REASONING_PLANNING"),
            expected_type=ReasoningPlan,
        )
        evidence = dependencies.store.get(
            _output_id(request.execution_id, "EVIDENCE_RESOLUTION_ENFORCED"),
            expected_type=EvidenceResolverOutput,
        )
        reasoning = dependencies.store.get(
            _output_id(request.execution_id, "REASONING"),
            expected_type=ReasoningEngineOutput,
        )
        decision_gate_input = build_decision_input(
            request_id=request.execution_id,
            reasoning_plan=plan,
            evidence_resolution=evidence,
            reasoning_output=reasoning,
            decision_context={
                "domain": request.product_scope.domain.lower(),
                **dict(request.customer_context),
            },
            strict_mode="STRICT",
        )
        output = AuthorityEnforcedDecisionGate().decide(
            build_authority_enforced_decision_input(
                request_id=request.execution_id,
                reconciliation=reconciliation,
                decision_gate_input=decision_gate_input,
            )
        )
        if not isinstance(output, AuthorityEnforcementResult):
            raise RealResponsePrefixError("authority-enforced decision did not return expected result")
        if output.enforcement_outcome != "DELEGATED_TO_DECISION_GATE" or not output.decision_gate_called:
            raise RealResponsePrefixError(
                f"authority-enforced decision blocked real path: {output.enforcement_outcome}; {output.basis}"
            )
        if output.decision_output is None:
            raise RealResponsePrefixError("delegated authority-enforced decision omitted DecisionGateOutput")

        output_id = _output_id(request.execution_id, stage)
        dependencies.store.put(output_id=output_id, value=output)
        decision_output = output.decision_output
        return build_raw_intelligence_stage_output(
            execution_id=request.execution_id,
            stage=stage,
            knowledge_snapshot_id=knowledge_snapshot_id,
            output_id=output_id,
            output_type="authority_enforcement_result",
            payload=asdict(output),
            limitations=decision_output.limitations,
            evidence_ids=tuple(decision_output.response_packet.approved_evidence_ids),
        )

    return prior + (
        build_intelligence_stage_adapter(
            stage="DECISION_GATE_AUTHORITY_ENFORCED",
            capability=decision,
        ),
    )


__all__ = ["build_real_response_decision_adapters"]
