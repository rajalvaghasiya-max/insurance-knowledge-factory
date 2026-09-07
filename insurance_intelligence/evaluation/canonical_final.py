"""Run FINAL_EVALUATION over the already executed canonical guarded response path.

The evaluator consumes captured orchestration results and the released response object.
It does not own or replay a private insurance-intelligence pipeline.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from insurance_intelligence.contracts.evaluation import EvaluationResult, EvaluationScenario
from insurance_intelligence.contracts.full_cycle import OrchestrationRequest, StageResult
from insurance_intelligence.evaluation.assertions import EvaluationAssertionEngine
from insurance_intelligence.evaluation.canonical_capture import capture_canonical_execution
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, TerminologyRegistry
from insurance_intelligence.orchestration.intelligence_adapters import (
    IntelligenceStageCapability,
    build_intelligence_stage_adapter,
    build_raw_intelligence_stage_output,
    execute_intelligence_stage,
)
from insurance_intelligence.orchestration.real_response_prefix import (
    RealResponsePrefixDependencies,
    RealResponsePrefixError,
)
from insurance_intelligence.orchestration.real_response_rendering import (
    build_real_response_rendering_adapters,
)
from insurance_intelligence.response.registry import ResponseFormatRegistry


@dataclass(frozen=True)
class CanonicalFinalEvaluationRun:
    stage_results: tuple[StageResult, ...]
    released_response_id: str | None
    evaluation_result: EvaluationResult | None

    @property
    def blocked(self) -> bool:
        return any(item.status in {"FAILED", "BLOCKED"} for item in self.stage_results)


def execute_canonical_final_evaluation(
    *,
    request: OrchestrationRequest,
    dependencies: RealResponsePrefixDependencies,
    style_registry: ExplanationStyleRegistry,
    response_registry: ResponseFormatRegistry,
    rendering_capability: IntelligenceStageCapability,
    evaluation_scenario: EvaluationScenario,
    terminology_registry: TerminologyRegistry | None = None,
    response_format: str = "STANDARD",
) -> CanonicalFinalEvaluationRun:
    """Execute the proven real path once and evaluate its captured released response.

    ``FINAL_EVALUATION`` is invoked only after the canonical prefix through
    ``LLM_RENDERING`` has succeeded or been explicitly marked ``NOT_REQUIRED``.
    The final-evaluation capability captures those existing results and scores them
    with the reusable deterministic assertion engine.
    """
    if not isinstance(request, OrchestrationRequest):
        raise RealResponsePrefixError("request must be OrchestrationRequest")
    if not isinstance(evaluation_scenario, EvaluationScenario):
        raise RealResponsePrefixError("evaluation_scenario must be EvaluationScenario")
    if request.requested_stage_order[-1] != "FINAL_EVALUATION":
        raise RealResponsePrefixError("request must include canonical FINAL_EVALUATION")

    prior_adapters = build_real_response_rendering_adapters(
        dependencies=dependencies,
        style_registry=style_registry,
        response_registry=response_registry,
        rendering_capability=rendering_capability,
        terminology_registry=terminology_registry,
        response_format=response_format,
    )
    if tuple(adapter.stage for adapter in prior_adapters) != request.requested_stage_order[:-1]:
        raise RealResponsePrefixError("real response adapters must match the canonical prefix before final evaluation")

    results: list[StageResult] = []
    prior_ids: tuple[str, ...] = (request.knowledge_snapshot_id or "",)
    released_response_id: str | None = None
    deterministic_response_id: str | None = None

    for sequence, adapter in enumerate(prior_adapters, start=1):
        result = execute_intelligence_stage(
            request=request,
            adapter=adapter,
            sequence=sequence,
            input_ids=prior_ids,
        )
        results.append(result)
        if result.status in {"FAILED", "BLOCKED"}:
            return CanonicalFinalEvaluationRun(
                stage_results=tuple(results),
                released_response_id=None,
                evaluation_result=None,
            )
        if result.status == "NOT_REQUIRED":
            if adapter.stage == "LLM_RENDERING":
                released_response_id = deterministic_response_id
            continue
        prior_ids = tuple(item.output_id for item in result.outputs)
        if adapter.stage == "RESPONSE_ASSEMBLY":
            deterministic_response_id = prior_ids[0]
        elif adapter.stage == "LLM_RENDERING":
            released_response_id = prior_ids[0]

    if released_response_id is None:
        released_response_id = deterministic_response_id
    if released_response_id is None:
        raise RealResponsePrefixError("canonical prefix produced no released response for final evaluation")

    evaluation_holder: dict[str, EvaluationResult] = {}

    def final_evaluation_capability(
        *,
        request: OrchestrationRequest,
        stage: str,
        input_ids: tuple[str, ...],
        knowledge_snapshot_id: str,
    ):
        if stage != "FINAL_EVALUATION":
            raise RealResponsePrefixError("final evaluation stage mismatch")
        if input_ids != (released_response_id,):
            raise RealResponsePrefixError("final evaluation must consume the released response identity")
        capture = capture_canonical_execution(
            request=request,
            stage_results=tuple(results),
            store=dependencies.store,
            released_response_id=released_response_id,
            scenario_id=evaluation_scenario.scenario_id,
            scenario_version=evaluation_scenario.scenario_version,
            fixture_id=f"canonical-fixture:{evaluation_scenario.scenario_id}",
        )
        evaluation = EvaluationAssertionEngine().evaluate(evaluation_scenario, capture)
        if evaluation.outcome != "PASS":
            raise RealResponsePrefixError(
                f"canonical final evaluation did not pass: {evaluation.outcome}; "
                f"failed={evaluation.failed_assertion_ids}; blocked={evaluation.blocked_reason}"
            )
        output_id = f"{request.execution_id}:real:final_evaluation"
        dependencies.store.put(output_id=output_id, value=evaluation)
        evaluation_holder["result"] = evaluation
        return build_raw_intelligence_stage_output(
            execution_id=request.execution_id,
            stage=stage,
            knowledge_snapshot_id=knowledge_snapshot_id,
            output_id=output_id,
            output_type="canonical_evaluation_result",
            payload=asdict(evaluation),
            evidence_ids=(released_response_id,),
        )

    final_adapter = build_intelligence_stage_adapter(
        stage="FINAL_EVALUATION",
        capability=final_evaluation_capability,
    )
    final_result = execute_intelligence_stage(
        request=request,
        adapter=final_adapter,
        sequence=len(prior_adapters) + 1,
        input_ids=(released_response_id,),
    )
    results.append(final_result)
    evaluation_result = evaluation_holder.get("result") if final_result.status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"} else None
    return CanonicalFinalEvaluationRun(
        stage_results=tuple(results),
        released_response_id=released_response_id,
        evaluation_result=evaluation_result,
    )


__all__ = ["CanonicalFinalEvaluationRun", "execute_canonical_final_evaluation"]
