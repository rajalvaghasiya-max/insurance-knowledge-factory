"""Governed orchestration contracts for knowledge build and intelligence response (MO-023A)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

SUPPORTED_CONTRACT_VERSION = "1.0"

EXECUTION_MODES = frozenset(
    {
        "KNOWLEDGE_BUILD",
        "KNOWLEDGE_REFRESH",
        "INTELLIGENCE_RESPONSE",
        "FULL_CYCLE_CERTIFICATION",
    }
)

STAGE_STATUSES = frozenset(
    {
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "SUCCEEDED_WITH_LIMITATIONS",
        "SKIPPED",
        "BLOCKED",
        "FAILED",
        "NOT_REQUIRED",
    }
)

CYCLE_STATUSES = frozenset(
    {
        "PENDING",
        "RUNNING",
        "SUCCEEDED",
        "SUCCEEDED_WITH_LIMITATIONS",
        "BLOCKED",
        "FAILED",
        "INVALID_INPUT",
    }
)

FAILURE_KINDS = frozenset(
    {
        "INVALID_INPUT",
        "DEPENDENCY_BLOCKED",
        "STAGE_ERROR",
        "MISSING_OUTPUT",
        "IDENTITY_MISMATCH",
        "STALE_KNOWLEDGE",
        "UNCERTIFIED_KNOWLEDGE",
        "PUBLICATION_BLOCKED",
        "EVALUATION_FAILED",
    }
)

TRACE_EVENT_TYPES = frozenset(
    {
        "EXECUTION_STARTED",
        "STAGE_STARTED",
        "STAGE_COMPLETED",
        "STAGE_SKIPPED",
        "STAGE_BLOCKED",
        "STAGE_FAILED",
        "KNOWLEDGE_SELECTED",
        "KNOWLEDGE_PUBLISHED",
        "FALLBACK_SELECTED",
        "EXECUTION_COMPLETED",
    }
)

KNOWLEDGE_BUILD_STAGE_ORDER = (
    "DISCOVERY",
    "SOURCE_ACQUISITION",
    "SOURCE_REGISTRATION",
    "PARSING",
    "QUALITY_AUDIT",
    "DOCUMENT_IDENTITY",
    "PRODUCT_IDENTITY",
    "EVIDENCE_ROUTING",
    "CANONICAL_KNOWLEDGE",
    "KNOWLEDGE_CERTIFICATION",
)

INTELLIGENCE_RESPONSE_STAGE_ORDER = (
    "REQUEST_INTAKE",
    "CERTIFIED_KNOWLEDGE_RETRIEVAL",
    "INTENT_ANALYSIS",
    "CONTEXT_BUILDING",
    "REASONING_PLANNING",
    "APPLICABILITY",
    "DECISION_GATE",
    "EXPLANATION",
    "RESPONSE_ASSEMBLY",
    "LLM_RENDERING",
    "FINAL_EVALUATION",
)

FULL_CYCLE_STAGE_ORDER = KNOWLEDGE_BUILD_STAGE_ORDER + INTELLIGENCE_RESPONSE_STAGE_ORDER
ALL_STAGE_NAMES = frozenset(FULL_CYCLE_STAGE_ORDER)

MODE_STAGE_ORDER = {
    "KNOWLEDGE_BUILD": KNOWLEDGE_BUILD_STAGE_ORDER,
    "KNOWLEDGE_REFRESH": KNOWLEDGE_BUILD_STAGE_ORDER,
    "INTELLIGENCE_RESPONSE": INTELLIGENCE_RESPONSE_STAGE_ORDER,
    "FULL_CYCLE_CERTIFICATION": FULL_CYCLE_STAGE_ORDER,
}


class FullCycleContractError(ValueError):
    """Raised when an orchestration contract is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FullCycleContractError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise FullCycleContractError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise FullCycleContractError(f"{label} values must be unique")
    return result


def _mapping(value: Mapping[str, object] | None) -> Mapping[str, object]:
    return dict(value or {})


@dataclass(frozen=True)
class ProductScope:
    domain: str
    insurer_id: str
    product_id: str
    product_variant_id: str | None
    source_scope_ids: tuple[str, ...]


def build_product_scope(
    *,
    domain: str,
    insurer_id: str,
    product_id: str,
    product_variant_id: str | None = None,
    source_scope_ids: Sequence[str] = (),
) -> ProductScope:
    variant = _text(product_variant_id, "product_scope.product_variant_id") if product_variant_id is not None else None
    return ProductScope(
        domain=_text(domain, "product_scope.domain"),
        insurer_id=_text(insurer_id, "product_scope.insurer_id"),
        product_id=_text(product_id, "product_scope.product_id"),
        product_variant_id=variant,
        source_scope_ids=_unique(source_scope_ids, "product_scope.source_scope_ids"),
    )


@dataclass(frozen=True)
class OrchestrationRequest:
    contract_version: str
    execution_id: str
    mode: str
    product_scope: ProductScope
    question: str | None
    audience: str | None
    customer_context: Mapping[str, object]
    knowledge_snapshot_id: str | None
    force_refresh: bool
    allow_llm_rendering: bool
    requested_stage_order: tuple[str, ...]


def build_orchestration_request(
    *,
    execution_id: str,
    mode: str,
    product_scope: ProductScope,
    question: str | None = None,
    audience: str | None = None,
    customer_context: Mapping[str, object] | None = None,
    knowledge_snapshot_id: str | None = None,
    force_refresh: bool = False,
    allow_llm_rendering: bool = True,
    requested_stage_order: Sequence[str] | None = None,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> OrchestrationRequest:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise FullCycleContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    if not isinstance(product_scope, ProductScope):
        raise FullCycleContractError("product_scope must be a validated ProductScope")
    selected_mode = _member(mode, EXECUTION_MODES, "request.mode")
    if not isinstance(force_refresh, bool) or not isinstance(allow_llm_rendering, bool):
        raise FullCycleContractError("force_refresh and allow_llm_rendering must be boolean")

    requires_question = selected_mode in {"INTELLIGENCE_RESPONSE", "FULL_CYCLE_CERTIFICATION"}
    if requires_question:
        resolved_question = _text(question, "request.question")
        resolved_audience = _text(audience, "request.audience")
    else:
        if question is not None or audience is not None or customer_context:
            raise FullCycleContractError("knowledge build modes cannot contain response-runtime inputs")
        resolved_question = None
        resolved_audience = None

    snapshot = _text(knowledge_snapshot_id, "request.knowledge_snapshot_id") if knowledge_snapshot_id is not None else None
    if selected_mode == "INTELLIGENCE_RESPONSE" and snapshot is None:
        raise FullCycleContractError("INTELLIGENCE_RESPONSE requires a certified knowledge_snapshot_id")
    if selected_mode in {"KNOWLEDGE_BUILD", "FULL_CYCLE_CERTIFICATION"} and snapshot is not None:
        raise FullCycleContractError(f"{selected_mode} cannot begin from an existing knowledge snapshot")
    if selected_mode == "KNOWLEDGE_BUILD" and force_refresh:
        raise FullCycleContractError("KNOWLEDGE_BUILD cannot force refresh; use KNOWLEDGE_REFRESH")
    if selected_mode == "KNOWLEDGE_REFRESH" and not force_refresh:
        raise FullCycleContractError("KNOWLEDGE_REFRESH requires force_refresh=True")

    canonical_order = MODE_STAGE_ORDER[selected_mode]
    stage_order = tuple(requested_stage_order) if requested_stage_order is not None else canonical_order
    if stage_order != canonical_order:
        raise FullCycleContractError("requested_stage_order must exactly match the governed order for the execution mode")

    return OrchestrationRequest(
        contract_version=contract_version,
        execution_id=_text(execution_id, "request.execution_id"),
        mode=selected_mode,
        product_scope=product_scope,
        question=resolved_question,
        audience=resolved_audience,
        customer_context=_mapping(customer_context),
        knowledge_snapshot_id=snapshot,
        force_refresh=force_refresh,
        allow_llm_rendering=allow_llm_rendering,
        requested_stage_order=stage_order,
    )


@dataclass(frozen=True)
class StageOutputReference:
    output_id: str
    output_type: str
    content_digest: str
    evidence_ids: tuple[str, ...]


def build_stage_output_reference(
    *, output_id: str, output_type: str, content_digest: str, evidence_ids: Sequence[str] = ()
) -> StageOutputReference:
    return StageOutputReference(
        output_id=_text(output_id, "output.output_id"),
        output_type=_text(output_type, "output.output_type"),
        content_digest=_text(content_digest, "output.content_digest"),
        evidence_ids=_unique(evidence_ids, "output.evidence_ids"),
    )


@dataclass(frozen=True)
class FailureRecord:
    failure_id: str
    stage: str
    failure_kind: str
    message: str
    retryable: bool
    blocked_stage_names: tuple[str, ...]


def build_failure_record(
    *,
    failure_id: str,
    stage: str,
    failure_kind: str,
    message: str,
    retryable: bool = False,
    blocked_stage_names: Sequence[str] = (),
) -> FailureRecord:
    if not isinstance(retryable, bool):
        raise FullCycleContractError("failure.retryable must be boolean")
    blocked = _unique(blocked_stage_names, "failure.blocked_stage_names")
    unknown = set(blocked) - ALL_STAGE_NAMES
    if unknown:
        raise FullCycleContractError(f"failure contains unknown blocked stages: {sorted(unknown)}")
    return FailureRecord(
        failure_id=_text(failure_id, "failure.failure_id"),
        stage=_member(stage, ALL_STAGE_NAMES, "failure.stage"),
        failure_kind=_member(failure_kind, FAILURE_KINDS, "failure.failure_kind"),
        message=_text(message, "failure.message"),
        retryable=retryable,
        blocked_stage_names=blocked,
    )


@dataclass(frozen=True)
class StageResult:
    execution_id: str
    stage: str
    sequence: int
    status: str
    input_ids: tuple[str, ...]
    outputs: tuple[StageOutputReference, ...]
    limitations: tuple[str, ...]
    failure: FailureRecord | None


def build_stage_result(
    *,
    execution_id: str,
    stage: str,
    sequence: int,
    status: str,
    input_ids: Sequence[str] = (),
    outputs: Sequence[StageOutputReference] = (),
    limitations: Sequence[str] = (),
    failure: FailureRecord | None = None,
) -> StageResult:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise FullCycleContractError("stage_result.sequence must be a positive integer")
    selected_stage = _member(stage, ALL_STAGE_NAMES, "stage_result.stage")
    selected_status = _member(status, STAGE_STATUSES, "stage_result.status")
    output_values = tuple(outputs)
    if len(output_values) != len({item.output_id for item in output_values}):
        raise FullCycleContractError("stage result output IDs must be unique")
    if any(not isinstance(item, StageOutputReference) for item in output_values):
        raise FullCycleContractError("stage result outputs must be validated StageOutputReference values")
    failure_status = selected_status in {"BLOCKED", "FAILED"}
    if failure_status != (failure is not None):
        raise FullCycleContractError("BLOCKED/FAILED stage results require one failure; other statuses prohibit it")
    if failure is not None and failure.stage != selected_stage:
        raise FullCycleContractError("failure stage must match stage result")
    if selected_status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"} and not output_values:
        raise FullCycleContractError("successful stage results require at least one output")
    if selected_status == "SUCCEEDED_WITH_LIMITATIONS" and not limitations:
        raise FullCycleContractError("SUCCEEDED_WITH_LIMITATIONS requires limitations")
    if selected_status in {"PENDING", "RUNNING", "SKIPPED", "BLOCKED", "FAILED", "NOT_REQUIRED"} and output_values:
        raise FullCycleContractError(f"{selected_status} stage results cannot expose outputs")
    return StageResult(
        execution_id=_text(execution_id, "stage_result.execution_id"),
        stage=selected_stage,
        sequence=sequence,
        status=selected_status,
        input_ids=_unique(input_ids, "stage_result.input_ids"),
        outputs=output_values,
        limitations=_unique(limitations, "stage_result.limitations"),
        failure=failure,
    )


@dataclass(frozen=True)
class ExecutionTraceEvent:
    event_id: str
    execution_id: str
    sequence: int
    event_type: str
    stage: str | None
    reference_ids: tuple[str, ...]
    message: str


def build_trace_event(
    *,
    event_id: str,
    execution_id: str,
    sequence: int,
    event_type: str,
    message: str,
    stage: str | None = None,
    reference_ids: Sequence[str] = (),
) -> ExecutionTraceEvent:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise FullCycleContractError("trace.sequence must be a positive integer")
    selected_stage = _member(stage, ALL_STAGE_NAMES, "trace.stage") if stage is not None else None
    selected_event = _member(event_type, TRACE_EVENT_TYPES, "trace.event_type")
    stage_events = {
        "STAGE_STARTED",
        "STAGE_COMPLETED",
        "STAGE_SKIPPED",
        "STAGE_BLOCKED",
        "STAGE_FAILED",
        "KNOWLEDGE_SELECTED",
        "KNOWLEDGE_PUBLISHED",
        "FALLBACK_SELECTED",
    }
    if (selected_event in stage_events) != (selected_stage is not None):
        raise FullCycleContractError("stage-scoped trace events require stage; execution events prohibit stage")
    return ExecutionTraceEvent(
        event_id=_text(event_id, "trace.event_id"),
        execution_id=_text(execution_id, "trace.execution_id"),
        sequence=sequence,
        event_type=selected_event,
        stage=selected_stage,
        reference_ids=_unique(reference_ids, "trace.reference_ids"),
        message=_text(message, "trace.message"),
    )


@dataclass(frozen=True)
class FullCycleResult:
    contract_version: str
    execution_id: str
    mode: str
    status: str
    stage_results: tuple[StageResult, ...]
    trace: tuple[ExecutionTraceEvent, ...]
    knowledge_snapshot_id: str | None
    deterministic_response_id: str | None
    released_response_id: str | None
    evaluation_report_id: str | None
    limitations: tuple[str, ...]


def build_full_cycle_result(
    *,
    execution_id: str,
    mode: str,
    status: str,
    stage_results: Sequence[StageResult],
    trace: Sequence[ExecutionTraceEvent],
    knowledge_snapshot_id: str | None = None,
    deterministic_response_id: str | None = None,
    released_response_id: str | None = None,
    evaluation_report_id: str | None = None,
    limitations: Sequence[str] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> FullCycleResult:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise FullCycleContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    eid = _text(execution_id, "result.execution_id")
    selected_mode = _member(mode, EXECUTION_MODES, "result.mode")
    selected_status = _member(status, CYCLE_STATUSES, "result.status")
    stages = tuple(stage_results)
    events = tuple(trace)
    if any(item.execution_id != eid for item in stages) or any(item.execution_id != eid for item in events):
        raise FullCycleContractError("all stage results and trace events must match result.execution_id")
    if len(stages) != len({item.stage for item in stages}):
        raise FullCycleContractError("full-cycle result stage names must be unique")
    if [item.sequence for item in stages] != list(range(1, len(stages) + 1)):
        raise FullCycleContractError("stage result sequences must be contiguous from 1")
    expected = MODE_STAGE_ORDER[selected_mode]
    if tuple(item.stage for item in stages) != expected:
        raise FullCycleContractError("stage results must exactly match the governed order for the execution mode")
    if [item.sequence for item in events] != list(range(1, len(events) + 1)):
        raise FullCycleContractError("trace sequences must be contiguous from 1")
    if len(events) != len({item.event_id for item in events}):
        raise FullCycleContractError("trace event IDs must be unique")

    snapshot = _text(knowledge_snapshot_id, "result.knowledge_snapshot_id") if knowledge_snapshot_id is not None else None
    deterministic_id = _text(deterministic_response_id, "result.deterministic_response_id") if deterministic_response_id is not None else None
    released_id = _text(released_response_id, "result.released_response_id") if released_response_id is not None else None
    report_id = _text(evaluation_report_id, "result.evaluation_report_id") if evaluation_report_id is not None else None

    is_response_mode = selected_mode in {"INTELLIGENCE_RESPONSE", "FULL_CYCLE_CERTIFICATION"}
    if selected_status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}:
        if snapshot is None:
            raise FullCycleContractError("successful executions require knowledge_snapshot_id")
        if is_response_mode and (deterministic_id is None or released_id is None or report_id is None):
            raise FullCycleContractError("successful response executions require deterministic, released, and evaluation IDs")
        if not is_response_mode and any(value is not None for value in (deterministic_id, released_id, report_id)):
            raise FullCycleContractError("knowledge-only executions cannot expose response or evaluation IDs")
        if any(item.status in {"FAILED", "BLOCKED", "PENDING", "RUNNING"} for item in stages):
            raise FullCycleContractError("successful execution cannot contain failed, blocked, pending, or running stages")
    if selected_status == "SUCCEEDED_WITH_LIMITATIONS" and not limitations:
        raise FullCycleContractError("SUCCEEDED_WITH_LIMITATIONS requires limitations")
    if selected_status in {"BLOCKED", "FAILED"} and not any(item.status in {"BLOCKED", "FAILED"} for item in stages):
        raise FullCycleContractError("blocked or failed execution requires a blocked or failed stage")

    return FullCycleResult(
        contract_version=contract_version,
        execution_id=eid,
        mode=selected_mode,
        status=selected_status,
        stage_results=stages,
        trace=events,
        knowledge_snapshot_id=snapshot,
        deterministic_response_id=deterministic_id,
        released_response_id=released_id,
        evaluation_report_id=report_id,
        limitations=_unique(limitations, "result.limitations"),
    )
