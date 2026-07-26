"""Governed adapters for Knowledge Factory orchestration stages (MO-023B)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable, Mapping, Protocol, Sequence

from insurance_intelligence.contracts.full_cycle import (
    KNOWLEDGE_BUILD_STAGE_ORDER,
    FailureRecord,
    OrchestrationRequest,
    StageOutputReference,
    StageResult,
    build_failure_record,
    build_stage_output_reference,
    build_stage_result,
)


class KnowledgeAdapterError(ValueError):
    """Raised when a Knowledge Factory adapter violates its governed boundary."""


@dataclass(frozen=True)
class RawKnowledgeStageOutput:
    """Minimal provider-neutral output returned by an existing Knowledge Factory capability."""

    output_id: str
    output_type: str
    payload: Mapping[str, object]
    evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class KnowledgeStageCapability(Protocol):
    def __call__(
        self,
        *,
        request: OrchestrationRequest,
        stage: str,
        input_ids: tuple[str, ...],
    ) -> RawKnowledgeStageOutput: ...


@dataclass(frozen=True)
class KnowledgeStageAdapter:
    stage: str
    capability: KnowledgeStageCapability


@dataclass(frozen=True)
class KnowledgeAdapterRun:
    execution_id: str
    stage_results: tuple[StageResult, ...]
    output_ids: tuple[str, ...]
    blocked: bool


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeAdapterError(f"{label} must be a non-empty string")
    return value.strip()


def _canonical_digest(payload: Mapping[str, object]) -> str:
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise KnowledgeAdapterError("stage payload must be canonical JSON-compatible data") from exc
    return sha256(encoded.encode("utf-8")).hexdigest()


def build_raw_knowledge_stage_output(
    *,
    output_id: str,
    output_type: str,
    payload: Mapping[str, object],
    evidence_ids: Sequence[str] = (),
    limitations: Sequence[str] = (),
) -> RawKnowledgeStageOutput:
    if not isinstance(payload, Mapping) or not payload:
        raise KnowledgeAdapterError("payload must be a non-empty mapping")
    evidence = tuple(_text(value, "evidence_ids[]") for value in evidence_ids)
    limits = tuple(_text(value, "limitations[]") for value in limitations)
    if len(evidence) != len(set(evidence)) or len(limits) != len(set(limits)):
        raise KnowledgeAdapterError("evidence IDs and limitations must be unique")
    _canonical_digest(payload)
    return RawKnowledgeStageOutput(
        output_id=_text(output_id, "output_id"),
        output_type=_text(output_type, "output_type"),
        payload=dict(payload),
        evidence_ids=evidence,
        limitations=limits,
    )


def build_knowledge_stage_adapter(*, stage: str, capability: KnowledgeStageCapability) -> KnowledgeStageAdapter:
    selected = _text(stage, "stage")
    if selected not in KNOWLEDGE_BUILD_STAGE_ORDER:
        raise KnowledgeAdapterError(f"stage must be a governed knowledge stage; got {selected!r}")
    if not callable(capability):
        raise KnowledgeAdapterError("capability must be callable")
    return KnowledgeStageAdapter(stage=selected, capability=capability)


def _normalise_output(raw: RawKnowledgeStageOutput) -> StageOutputReference:
    if not isinstance(raw, RawKnowledgeStageOutput):
        raise KnowledgeAdapterError("capability must return RawKnowledgeStageOutput")
    return build_stage_output_reference(
        output_id=raw.output_id,
        output_type=raw.output_type,
        content_digest=_canonical_digest(raw.payload),
        evidence_ids=raw.evidence_ids,
    )


def execute_knowledge_stage(
    *,
    request: OrchestrationRequest,
    adapter: KnowledgeStageAdapter,
    sequence: int,
    input_ids: Sequence[str] = (),
) -> StageResult:
    if request.mode not in {"KNOWLEDGE_BUILD", "KNOWLEDGE_REFRESH", "FULL_CYCLE_CERTIFICATION"}:
        raise KnowledgeAdapterError("knowledge adapters cannot run in INTELLIGENCE_RESPONSE mode")
    expected_stage = request.requested_stage_order[sequence - 1] if 0 < sequence <= len(request.requested_stage_order) else None
    if expected_stage != adapter.stage:
        raise KnowledgeAdapterError("adapter stage and sequence must match the governed request order")
    inputs = tuple(_text(value, "input_ids[]") for value in input_ids)
    try:
        raw = adapter.capability(request=request, stage=adapter.stage, input_ids=inputs)
        output = _normalise_output(raw)
        status = "SUCCEEDED_WITH_LIMITATIONS" if raw.limitations else "SUCCEEDED"
        return build_stage_result(
            execution_id=request.execution_id,
            stage=adapter.stage,
            sequence=sequence,
            status=status,
            input_ids=inputs,
            outputs=(output,),
            limitations=raw.limitations,
        )
    except Exception as exc:  # adapter boundary deliberately normalises all capability failures
        failure = build_failure_record(
            failure_id=f"failure:{request.execution_id}:{adapter.stage.lower()}",
            stage=adapter.stage,
            failure_kind="STAGE_ERROR",
            message=str(exc) or exc.__class__.__name__,
            retryable=False,
            blocked_stage_names=request.requested_stage_order[sequence:],
        )
        return build_stage_result(
            execution_id=request.execution_id,
            stage=adapter.stage,
            sequence=sequence,
            status="FAILED",
            input_ids=inputs,
            failure=failure,
        )


def execute_knowledge_adapter_chain(
    *,
    request: OrchestrationRequest,
    adapters: Sequence[KnowledgeStageAdapter],
) -> KnowledgeAdapterRun:
    required = tuple(request.requested_stage_order[: len(KNOWLEDGE_BUILD_STAGE_ORDER)])
    by_stage = {adapter.stage: adapter for adapter in adapters}
    if len(by_stage) != len(tuple(adapters)):
        raise KnowledgeAdapterError("adapter stages must be unique")
    if tuple(adapter.stage for adapter in adapters) != required:
        raise KnowledgeAdapterError("adapters must exactly match governed knowledge-stage order")

    results: list[StageResult] = []
    prior_outputs: tuple[str, ...] = ()
    blocked = False
    for sequence, stage in enumerate(required, start=1):
        if blocked:
            failure = build_failure_record(
                failure_id=f"failure:{request.execution_id}:{stage.lower()}:blocked",
                stage=stage,
                failure_kind="DEPENDENCY_BLOCKED",
                message="A prior knowledge stage failed.",
                blocked_stage_names=required[sequence:],
            )
            results.append(
                build_stage_result(
                    execution_id=request.execution_id,
                    stage=stage,
                    sequence=sequence,
                    status="BLOCKED",
                    input_ids=prior_outputs,
                    failure=failure,
                )
            )
            continue
        result = execute_knowledge_stage(
            request=request,
            adapter=by_stage[stage],
            sequence=sequence,
            input_ids=prior_outputs,
        )
        results.append(result)
        if result.status == "FAILED":
            blocked = True
        else:
            prior_outputs = tuple(output.output_id for output in result.outputs)

    return KnowledgeAdapterRun(
        execution_id=request.execution_id,
        stage_results=tuple(results),
        output_ids=prior_outputs if not blocked else (),
        blocked=blocked,
    )


def deterministic_fake_capability(
    *,
    output_type: str,
    payload_factory: Callable[[OrchestrationRequest, str, tuple[str, ...]], Mapping[str, object]] | None = None,
    limitations: Sequence[str] = (),
) -> KnowledgeStageCapability:
    """Build an offline deterministic fake used by orchestration tests."""

    resolved_type = _text(output_type, "output_type")
    resolved_limits = tuple(_text(value, "limitations[]") for value in limitations)

    def capability(*, request: OrchestrationRequest, stage: str, input_ids: tuple[str, ...]) -> RawKnowledgeStageOutput:
        payload = (
            payload_factory(request, stage, input_ids)
            if payload_factory is not None
            else {
                "execution_id": request.execution_id,
                "stage": stage,
                "input_ids": list(input_ids),
                "product_id": request.product_scope.product_id,
            }
        )
        digest = _canonical_digest(payload)
        return build_raw_knowledge_stage_output(
            output_id=f"{request.execution_id}:{stage.lower()}:{digest[:12]}",
            output_type=resolved_type,
            payload=payload,
            limitations=resolved_limits,
        )

    return capability
