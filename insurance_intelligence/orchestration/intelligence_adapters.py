"""Governed adapters for intelligence-response orchestration stages (MO-023C)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Callable, Mapping, Protocol, Sequence

from insurance_intelligence.contracts.full_cycle import (
    INTELLIGENCE_RESPONSE_STAGE_ORDER,
    KNOWLEDGE_BUILD_STAGE_ORDER,
    OrchestrationRequest,
    StageOutputReference,
    StageResult,
    build_failure_record,
    build_stage_output_reference,
    build_stage_result,
)


class IntelligenceAdapterError(ValueError):
    """Raised when an intelligence runtime adapter violates its governed boundary."""


@dataclass(frozen=True)
class RawIntelligenceStageOutput:
    """Minimal provider-neutral output returned by an existing intelligence capability."""

    execution_id: str
    stage: str
    knowledge_snapshot_id: str
    output_id: str
    output_type: str
    payload: Mapping[str, object]
    evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


class IntelligenceStageCapability(Protocol):
    def __call__(
        self,
        *,
        request: OrchestrationRequest,
        stage: str,
        input_ids: tuple[str, ...],
        knowledge_snapshot_id: str,
    ) -> RawIntelligenceStageOutput: ...


@dataclass(frozen=True)
class IntelligenceStageAdapter:
    stage: str
    capability: IntelligenceStageCapability


@dataclass(frozen=True)
class IntelligenceAdapterRun:
    execution_id: str
    knowledge_snapshot_id: str
    stage_results: tuple[StageResult, ...]
    output_ids: tuple[str, ...]
    deterministic_response_id: str | None
    released_response_id: str | None
    evaluation_report_id: str | None
    blocked: bool


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntelligenceAdapterError(f"{label} must be a non-empty string")
    return value.strip()


def _canonical_digest(payload: Mapping[str, object]) -> str:
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise IntelligenceAdapterError("stage payload must be canonical JSON-compatible data") from exc
    return sha256(encoded.encode("utf-8")).hexdigest()


def build_raw_intelligence_stage_output(
    *,
    execution_id: str,
    stage: str,
    knowledge_snapshot_id: str,
    output_id: str,
    output_type: str,
    payload: Mapping[str, object],
    evidence_ids: Sequence[str] = (),
    limitations: Sequence[str] = (),
) -> RawIntelligenceStageOutput:
    selected_stage = _text(stage, "stage")
    if selected_stage not in INTELLIGENCE_RESPONSE_STAGE_ORDER:
        raise IntelligenceAdapterError(f"stage must be a governed intelligence stage; got {selected_stage!r}")
    if not isinstance(payload, Mapping) or not payload:
        raise IntelligenceAdapterError("payload must be a non-empty mapping")
    evidence = tuple(_text(value, "evidence_ids[]") for value in evidence_ids)
    limits = tuple(_text(value, "limitations[]") for value in limitations)
    if len(evidence) != len(set(evidence)) or len(limits) != len(set(limits)):
        raise IntelligenceAdapterError("evidence IDs and limitations must be unique")
    _canonical_digest(payload)
    return RawIntelligenceStageOutput(
        execution_id=_text(execution_id, "execution_id"),
        stage=selected_stage,
        knowledge_snapshot_id=_text(knowledge_snapshot_id, "knowledge_snapshot_id"),
        output_id=_text(output_id, "output_id"),
        output_type=_text(output_type, "output_type"),
        payload=dict(payload),
        evidence_ids=evidence,
        limitations=limits,
    )


def build_intelligence_stage_adapter(
    *, stage: str, capability: IntelligenceStageCapability
) -> IntelligenceStageAdapter:
    selected = _text(stage, "stage")
    if selected not in INTELLIGENCE_RESPONSE_STAGE_ORDER:
        raise IntelligenceAdapterError(f"stage must be a governed intelligence stage; got {selected!r}")
    if not callable(capability):
        raise IntelligenceAdapterError("capability must be callable")
    return IntelligenceStageAdapter(stage=selected, capability=capability)


def _response_offset(request: OrchestrationRequest) -> int:
    if request.mode == "INTELLIGENCE_RESPONSE":
        return 0
    if request.mode == "FULL_CYCLE_CERTIFICATION":
        return len(KNOWLEDGE_BUILD_STAGE_ORDER)
    raise IntelligenceAdapterError("intelligence adapters require INTELLIGENCE_RESPONSE or FULL_CYCLE_CERTIFICATION mode")


def _resolve_snapshot(request: OrchestrationRequest, supplied: str | None) -> str:
    if request.mode == "INTELLIGENCE_RESPONSE":
        expected = _text(request.knowledge_snapshot_id, "request.knowledge_snapshot_id")
        if supplied is not None and _text(supplied, "knowledge_snapshot_id") != expected:
            raise IntelligenceAdapterError("supplied knowledge snapshot must match the response request")
        return expected
    if request.mode == "FULL_CYCLE_CERTIFICATION":
        if supplied is None:
            raise IntelligenceAdapterError("full-cycle intelligence execution requires the newly certified knowledge snapshot")
        return _text(supplied, "knowledge_snapshot_id")
    raise IntelligenceAdapterError("knowledge-only modes cannot run intelligence adapters")


def _normalise_output(
    raw: RawIntelligenceStageOutput,
    *, request: OrchestrationRequest,
    stage: str,
    snapshot_id: str,
) -> StageOutputReference:
    if not isinstance(raw, RawIntelligenceStageOutput):
        raise IntelligenceAdapterError("capability must return RawIntelligenceStageOutput")
    if raw.execution_id != request.execution_id:
        raise IntelligenceAdapterError("capability output execution identity mismatch")
    if raw.stage != stage:
        raise IntelligenceAdapterError("capability output stage identity mismatch")
    if raw.knowledge_snapshot_id != snapshot_id:
        raise IntelligenceAdapterError("capability output knowledge snapshot identity mismatch")
    return build_stage_output_reference(
        output_id=raw.output_id,
        output_type=raw.output_type,
        content_digest=_canonical_digest(raw.payload),
        evidence_ids=raw.evidence_ids,
    )


def execute_intelligence_stage(
    *,
    request: OrchestrationRequest,
    adapter: IntelligenceStageAdapter,
    sequence: int,
    knowledge_snapshot_id: str | None = None,
    input_ids: Sequence[str] = (),
) -> StageResult:
    offset = _response_offset(request)
    local_index = sequence - offset - 1
    if local_index < 0 or local_index >= len(INTELLIGENCE_RESPONSE_STAGE_ORDER):
        raise IntelligenceAdapterError("sequence is outside the governed intelligence stage range")
    expected_stage = request.requested_stage_order[sequence - 1]
    if expected_stage != adapter.stage:
        raise IntelligenceAdapterError("adapter stage and sequence must match the governed request order")
    snapshot = _resolve_snapshot(request, knowledge_snapshot_id)
    inputs = tuple(_text(value, "input_ids[]") for value in input_ids)

    if adapter.stage == "LLM_RENDERING" and not request.allow_llm_rendering:
        return build_stage_result(
            execution_id=request.execution_id,
            stage=adapter.stage,
            sequence=sequence,
            status="NOT_REQUIRED",
            input_ids=inputs,
        )

    try:
        raw = adapter.capability(
            request=request,
            stage=adapter.stage,
            input_ids=inputs,
            knowledge_snapshot_id=snapshot,
        )
        output = _normalise_output(raw, request=request, stage=adapter.stage, snapshot_id=snapshot)
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
    except Exception as exc:  # runtime boundary deliberately normalises capability failures
        blocked = request.requested_stage_order[sequence:]
        failure = build_failure_record(
            failure_id=f"failure:{request.execution_id}:{adapter.stage.lower()}",
            stage=adapter.stage,
            failure_kind="STAGE_ERROR",
            message=str(exc) or exc.__class__.__name__,
            retryable=False,
            blocked_stage_names=blocked,
        )
        return build_stage_result(
            execution_id=request.execution_id,
            stage=adapter.stage,
            sequence=sequence,
            status="FAILED",
            input_ids=inputs,
            failure=failure,
        )


def execute_intelligence_adapter_chain(
    *,
    request: OrchestrationRequest,
    adapters: Sequence[IntelligenceStageAdapter],
    knowledge_snapshot_id: str | None = None,
) -> IntelligenceAdapterRun:
    snapshot = _resolve_snapshot(request, knowledge_snapshot_id)
    required = INTELLIGENCE_RESPONSE_STAGE_ORDER
    adapter_values = tuple(adapters)
    by_stage = {adapter.stage: adapter for adapter in adapter_values}
    if len(by_stage) != len(adapter_values):
        raise IntelligenceAdapterError("adapter stages must be unique")
    if tuple(adapter.stage for adapter in adapter_values) != required:
        raise IntelligenceAdapterError("adapters must exactly match governed intelligence-stage order")

    offset = _response_offset(request)
    results: list[StageResult] = []
    prior_outputs: tuple[str, ...] = (snapshot,)
    blocked = False
    deterministic_response_id: str | None = None
    released_response_id: str | None = None
    evaluation_report_id: str | None = None

    for local_sequence, stage in enumerate(required, start=1):
        sequence = offset + local_sequence
        if blocked:
            failure = build_failure_record(
                failure_id=f"failure:{request.execution_id}:{stage.lower()}:blocked",
                stage=stage,
                failure_kind="DEPENDENCY_BLOCKED",
                message="A prior intelligence stage failed.",
                blocked_stage_names=required[local_sequence:],
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

        result = execute_intelligence_stage(
            request=request,
            adapter=by_stage[stage],
            sequence=sequence,
            knowledge_snapshot_id=snapshot,
            input_ids=prior_outputs,
        )
        results.append(result)
        if result.status == "FAILED":
            blocked = True
            continue
        if result.status == "NOT_REQUIRED":
            if stage == "LLM_RENDERING":
                released_response_id = deterministic_response_id
            continue

        prior_outputs = tuple(output.output_id for output in result.outputs)
        if stage == "RESPONSE_ASSEMBLY":
            deterministic_response_id = prior_outputs[0]
        elif stage == "LLM_RENDERING":
            released_response_id = prior_outputs[0]
        elif stage == "FINAL_EVALUATION":
            evaluation_report_id = prior_outputs[0]

    if not blocked and released_response_id is None:
        released_response_id = deterministic_response_id

    return IntelligenceAdapterRun(
        execution_id=request.execution_id,
        knowledge_snapshot_id=snapshot,
        stage_results=tuple(results),
        output_ids=prior_outputs if not blocked else (),
        deterministic_response_id=deterministic_response_id if not blocked else None,
        released_response_id=released_response_id if not blocked else None,
        evaluation_report_id=evaluation_report_id if not blocked else None,
        blocked=blocked,
    )


def deterministic_fake_intelligence_capability(
    *,
    output_type: str,
    payload_factory: Callable[
        [OrchestrationRequest, str, tuple[str, ...], str], Mapping[str, object]
    ] | None = None,
    evidence_ids: Sequence[str] = (),
    limitations: Sequence[str] = (),
) -> IntelligenceStageCapability:
    """Build an offline deterministic fake used by orchestration tests."""

    resolved_type = _text(output_type, "output_type")
    resolved_evidence = tuple(_text(value, "evidence_ids[]") for value in evidence_ids)
    resolved_limits = tuple(_text(value, "limitations[]") for value in limitations)

    def capability(
        *,
        request: OrchestrationRequest,
        stage: str,
        input_ids: tuple[str, ...],
        knowledge_snapshot_id: str,
    ) -> RawIntelligenceStageOutput:
        payload = (
            payload_factory(request, stage, input_ids, knowledge_snapshot_id)
            if payload_factory is not None
            else {
                "execution_id": request.execution_id,
                "stage": stage,
                "input_ids": list(input_ids),
                "knowledge_snapshot_id": knowledge_snapshot_id,
                "question": request.question,
                "audience": request.audience,
                "product_id": request.product_scope.product_id,
            }
        )
        digest = _canonical_digest(payload)
        return build_raw_intelligence_stage_output(
            execution_id=request.execution_id,
            stage=stage,
            knowledge_snapshot_id=knowledge_snapshot_id,
            output_id=f"{request.execution_id}:{stage.lower()}:{digest[:12]}",
            output_type=resolved_type,
            payload=payload,
            evidence_ids=resolved_evidence,
            limitations=resolved_limits,
        )

    return capability
