"""Generic extension of the proven real response prefix through deterministic reasoning.

This module composes the existing real prefix with the existing ReasoningEngine without
changing planner, evidence, or reasoning semantics. It intentionally stops at REASONING.
For the Star PED factual pressure case this exercises only the documented-fact lane; it
does not prove genericity of conditional/applicability rule execution.
"""
from __future__ import annotations

from dataclasses import asdict

from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.reasoning import (
    ReasoningEngineOutput,
    build_input as build_reasoning_input,
)
from insurance_intelligence.contracts.reasoning_plan import ReasoningPlan
from insurance_intelligence.orchestration.intelligence_adapters import (
    build_intelligence_stage_adapter,
    build_raw_intelligence_stage_output,
)
from insurance_intelligence.orchestration.real_response_prefix import (
    RealResponsePrefixDependencies,
    RealResponsePrefixError,
    build_real_response_prefix_adapters,
)
from insurance_intelligence.reasoning.engine import ReasoningEngine


def _output_id(execution_id: str, stage: str) -> str:
    return f"{execution_id}:real:{stage.lower()}"


def build_real_response_reasoning_adapters(
    *, dependencies: RealResponsePrefixDependencies
):
    """Build the proven real prefix plus the canonical REASONING stage."""
    prefix = build_real_response_prefix_adapters(dependencies=dependencies)

    def reasoning(*, request, stage, input_ids, knowledge_snapshot_id):
        if stage != "REASONING":
            raise RealResponsePrefixError("reasoning stage mismatch")
        plan = dependencies.store.get(
            _output_id(request.execution_id, "REASONING_PLANNING"),
            expected_type=ReasoningPlan,
        )
        evidence = dependencies.store.get(
            _output_id(request.execution_id, "EVIDENCE_RESOLUTION_ENFORCED"),
            expected_type=EvidenceResolverOutput,
        )
        output = ReasoningEngine().reason(
            build_reasoning_input(
                request_id=request.execution_id,
                reasoning_plan=plan,
                evidence_resolution=evidence,
                reasoning_context=dict(request.customer_context),
                strict_mode="STRICT",
            )
        )
        if not isinstance(output, ReasoningEngineOutput):
            raise RealResponsePrefixError("reasoning engine did not return ReasoningEngineOutput")

        output_id = _output_id(request.execution_id, stage)
        dependencies.store.put(output_id=output_id, value=output)
        evidence_ids = tuple(
            sorted({evidence_id for finding in output.findings for evidence_id in finding.evidence_ids})
        )
        return build_raw_intelligence_stage_output(
            execution_id=request.execution_id,
            stage=stage,
            knowledge_snapshot_id=knowledge_snapshot_id,
            output_id=output_id,
            output_type="reasoning_engine_output",
            payload=asdict(output),
            limitations=output.limitations,
            evidence_ids=evidence_ids,
        )

    return prefix + (
        build_intelligence_stage_adapter(stage="REASONING", capability=reasoning),
    )


__all__ = ["build_real_response_reasoning_adapters"]
