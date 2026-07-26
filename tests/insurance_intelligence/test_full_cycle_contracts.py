from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.full_cycle import (
    FULL_CYCLE_STAGE_ORDER,
    INTELLIGENCE_RESPONSE_STAGE_ORDER,
    KNOWLEDGE_BUILD_STAGE_ORDER,
    FullCycleContractError,
    build_failure_record,
    build_full_cycle_result,
    build_orchestration_request,
    build_product_scope,
    build_stage_output_reference,
    build_stage_result,
    build_trace_event,
)


def scope():
    return build_product_scope(domain="health", insurer_id="star_health", product_id="star_comprehensive")


def output(stage: str):
    return build_stage_output_reference(
        output_id=f"out-{stage.lower()}", output_type=f"{stage}_OUTPUT", content_digest=f"sha256:{stage.lower()}"
    )


def successful_stages(mode: str, execution_id: str = "exec-1"):
    order = {
        "KNOWLEDGE_BUILD": KNOWLEDGE_BUILD_STAGE_ORDER,
        "KNOWLEDGE_REFRESH": KNOWLEDGE_BUILD_STAGE_ORDER,
        "INTELLIGENCE_RESPONSE": INTELLIGENCE_RESPONSE_STAGE_ORDER,
        "FULL_CYCLE_CERTIFICATION": FULL_CYCLE_STAGE_ORDER,
    }[mode]
    return tuple(
        build_stage_result(
            execution_id=execution_id,
            stage=stage,
            sequence=index,
            status="SUCCEEDED",
            outputs=(output(stage),),
        )
        for index, stage in enumerate(order, start=1)
    )


def execution_trace(execution_id: str = "exec-1"):
    return (
        build_trace_event(
            event_id="evt-1", execution_id=execution_id, sequence=1, event_type="EXECUTION_STARTED", message="started"
        ),
        build_trace_event(
            event_id="evt-2", execution_id=execution_id, sequence=2, event_type="EXECUTION_COMPLETED", message="done"
        ),
    )


def test_product_scope_is_immutable_and_normalized():
    value = build_product_scope(
        domain=" health ", insurer_id=" star_health ", product_id=" star_comprehensive ", source_scope_ids=("a", "b")
    )
    assert value.domain == "health"
    with pytest.raises(FrozenInstanceError):
        value.domain = "motor"  # type: ignore[misc]


def test_product_scope_rejects_duplicate_source_ids():
    with pytest.raises(FullCycleContractError, match="unique"):
        build_product_scope(domain="health", insurer_id="i", product_id="p", source_scope_ids=("a", "a"))


def test_knowledge_build_has_only_manufacturing_stages():
    request = build_orchestration_request(execution_id="e", mode="KNOWLEDGE_BUILD", product_scope=scope())
    assert request.requested_stage_order == KNOWLEDGE_BUILD_STAGE_ORDER
    assert "REQUEST_INTAKE" not in request.requested_stage_order


def test_intelligence_response_requires_certified_snapshot_and_question():
    request = build_orchestration_request(
        execution_id="e",
        mode="INTELLIGENCE_RESPONSE",
        product_scope=scope(),
        question="How does co-payment affect me?",
        audience="CUSTOMER",
        knowledge_snapshot_id="ks-1",
    )
    assert request.requested_stage_order == INTELLIGENCE_RESPONSE_STAGE_ORDER
    with pytest.raises(FullCycleContractError, match="knowledge_snapshot_id"):
        build_orchestration_request(
            execution_id="e", mode="INTELLIGENCE_RESPONSE", product_scope=scope(), question="q", audience="CUSTOMER"
        )


def test_full_cycle_certification_contains_both_cycles_and_rejects_snapshot():
    request = build_orchestration_request(
        execution_id="e",
        mode="FULL_CYCLE_CERTIFICATION",
        product_scope=scope(),
        question="q",
        audience="ADVISOR",
    )
    assert request.requested_stage_order == FULL_CYCLE_STAGE_ORDER
    with pytest.raises(FullCycleContractError, match="cannot begin"):
        build_orchestration_request(
            execution_id="e",
            mode="FULL_CYCLE_CERTIFICATION",
            product_scope=scope(),
            question="q",
            audience="ADVISOR",
            knowledge_snapshot_id="ks-old",
        )


def test_knowledge_modes_reject_runtime_question_context():
    with pytest.raises(FullCycleContractError, match="cannot contain"):
        build_orchestration_request(
            execution_id="e", mode="KNOWLEDGE_BUILD", product_scope=scope(), question="q", audience="CUSTOMER"
        )


def test_refresh_mode_requires_force_refresh():
    with pytest.raises(FullCycleContractError, match="force_refresh=True"):
        build_orchestration_request(execution_id="e", mode="KNOWLEDGE_REFRESH", product_scope=scope())
    assert build_orchestration_request(
        execution_id="e", mode="KNOWLEDGE_REFRESH", product_scope=scope(), force_refresh=True
    ).force_refresh


def test_build_mode_rejects_force_refresh():
    with pytest.raises(FullCycleContractError, match="use KNOWLEDGE_REFRESH"):
        build_orchestration_request(execution_id="e", mode="KNOWLEDGE_BUILD", product_scope=scope(), force_refresh=True)


def test_request_rejects_stage_reordering_or_omission():
    with pytest.raises(FullCycleContractError, match="exactly match"):
        build_orchestration_request(
            execution_id="e",
            mode="KNOWLEDGE_BUILD",
            product_scope=scope(),
            requested_stage_order=tuple(reversed(KNOWLEDGE_BUILD_STAGE_ORDER)),
        )


def test_request_rejects_unsupported_contract_version():
    with pytest.raises(FullCycleContractError, match="contract_version"):
        build_orchestration_request(execution_id="e", mode="KNOWLEDGE_BUILD", product_scope=scope(), contract_version="2")


def test_output_reference_requires_unique_evidence_ids():
    with pytest.raises(FullCycleContractError, match="unique"):
        build_stage_output_reference(output_id="o", output_type="x", content_digest="d", evidence_ids=("e", "e"))


def test_successful_stage_requires_output():
    with pytest.raises(FullCycleContractError, match="at least one output"):
        build_stage_result(execution_id="e", stage="DISCOVERY", sequence=1, status="SUCCEEDED")


def test_limited_stage_requires_limitation():
    with pytest.raises(FullCycleContractError, match="requires limitations"):
        build_stage_result(
            execution_id="e", stage="DISCOVERY", sequence=1, status="SUCCEEDED_WITH_LIMITATIONS", outputs=(output("DISCOVERY"),)
        )


def test_failed_stage_requires_matching_failure():
    with pytest.raises(FullCycleContractError, match="require one failure"):
        build_stage_result(execution_id="e", stage="DISCOVERY", sequence=1, status="FAILED")
    failure = build_failure_record(
        failure_id="f", stage="PARSING", failure_kind="STAGE_ERROR", message="parse failed"
    )
    with pytest.raises(FullCycleContractError, match="must match"):
        build_stage_result(execution_id="e", stage="QUALITY_AUDIT", sequence=1, status="FAILED", failure=failure)


def test_nonterminal_stage_cannot_expose_output():
    with pytest.raises(FullCycleContractError, match="cannot expose outputs"):
        build_stage_result(
            execution_id="e", stage="DISCOVERY", sequence=1, status="RUNNING", outputs=(output("DISCOVERY"),)
        )


def test_failure_rejects_unknown_blocked_stage():
    with pytest.raises(FullCycleContractError, match="unknown blocked"):
        build_failure_record(
            failure_id="f", stage="PARSING", failure_kind="STAGE_ERROR", message="x", blocked_stage_names=("UNKNOWN",)
        )


def test_trace_stage_event_requires_stage():
    with pytest.raises(FullCycleContractError, match="require stage"):
        build_trace_event(
            event_id="e", execution_id="x", sequence=1, event_type="STAGE_STARTED", message="start"
        )


def test_trace_execution_event_prohibits_stage():
    with pytest.raises(FullCycleContractError, match="prohibit stage"):
        build_trace_event(
            event_id="e", execution_id="x", sequence=1, event_type="EXECUTION_STARTED", stage="DISCOVERY", message="start"
        )


def test_successful_knowledge_result_requires_snapshot_and_no_response_ids():
    value = build_full_cycle_result(
        execution_id="exec-1",
        mode="KNOWLEDGE_BUILD",
        status="SUCCEEDED",
        stage_results=successful_stages("KNOWLEDGE_BUILD"),
        trace=execution_trace(),
        knowledge_snapshot_id="ks-1",
    )
    assert value.released_response_id is None
    with pytest.raises(FullCycleContractError, match="cannot expose response"):
        build_full_cycle_result(
            execution_id="exec-1",
            mode="KNOWLEDGE_BUILD",
            status="SUCCEEDED",
            stage_results=successful_stages("KNOWLEDGE_BUILD"),
            trace=execution_trace(),
            knowledge_snapshot_id="ks-1",
            released_response_id="r",
        )


def test_successful_response_result_requires_all_linkage_ids():
    with pytest.raises(FullCycleContractError, match="deterministic, released, and evaluation"):
        build_full_cycle_result(
            execution_id="exec-1",
            mode="INTELLIGENCE_RESPONSE",
            status="SUCCEEDED",
            stage_results=successful_stages("INTELLIGENCE_RESPONSE"),
            trace=execution_trace(),
            knowledge_snapshot_id="ks-1",
            deterministic_response_id="d",
            released_response_id="r",
        )


def test_successful_response_result_preserves_deterministic_and_released_linkage():
    value = build_full_cycle_result(
        execution_id="exec-1",
        mode="INTELLIGENCE_RESPONSE",
        status="SUCCEEDED",
        stage_results=successful_stages("INTELLIGENCE_RESPONSE"),
        trace=execution_trace(),
        knowledge_snapshot_id="ks-1",
        deterministic_response_id="d",
        released_response_id="r",
        evaluation_report_id="eval",
    )
    assert value.deterministic_response_id == "d"
    assert value.released_response_id == "r"


def test_result_rejects_wrong_stage_order():
    stages = list(successful_stages("KNOWLEDGE_BUILD"))
    stages[0], stages[1] = stages[1], stages[0]
    stages = [
        build_stage_result(
            execution_id=item.execution_id,
            stage=item.stage,
            sequence=index,
            status=item.status,
            outputs=item.outputs,
        )
        for index, item in enumerate(stages, start=1)
    ]
    with pytest.raises(FullCycleContractError, match="governed order"):
        build_full_cycle_result(
            execution_id="exec-1",
            mode="KNOWLEDGE_BUILD",
            status="SUCCEEDED",
            stage_results=stages,
            trace=execution_trace(),
            knowledge_snapshot_id="ks-1",
        )


def test_result_rejects_execution_identity_mismatch():
    with pytest.raises(FullCycleContractError, match="execution_id"):
        build_full_cycle_result(
            execution_id="exec-1",
            mode="KNOWLEDGE_BUILD",
            status="SUCCEEDED",
            stage_results=successful_stages("KNOWLEDGE_BUILD", execution_id="other"),
            trace=execution_trace(),
            knowledge_snapshot_id="ks-1",
        )


def test_result_rejects_noncontiguous_trace_sequence():
    trace = (
        build_trace_event(
            event_id="evt-1", execution_id="exec-1", sequence=1, event_type="EXECUTION_STARTED", message="started"
        ),
        build_trace_event(
            event_id="evt-2", execution_id="exec-1", sequence=3, event_type="EXECUTION_COMPLETED", message="done"
        ),
    )
    with pytest.raises(FullCycleContractError, match="trace sequences"):
        build_full_cycle_result(
            execution_id="exec-1",
            mode="KNOWLEDGE_BUILD",
            status="SUCCEEDED",
            stage_results=successful_stages("KNOWLEDGE_BUILD"),
            trace=trace,
            knowledge_snapshot_id="ks-1",
        )


def test_blocked_result_requires_blocked_or_failed_stage():
    with pytest.raises(FullCycleContractError, match="requires a blocked or failed stage"):
        build_full_cycle_result(
            execution_id="exec-1",
            mode="KNOWLEDGE_BUILD",
            status="BLOCKED",
            stage_results=successful_stages("KNOWLEDGE_BUILD"),
            trace=execution_trace(),
        )


def test_succeeded_with_limitations_requires_result_limitation():
    with pytest.raises(FullCycleContractError, match="requires limitations"):
        build_full_cycle_result(
            execution_id="exec-1",
            mode="KNOWLEDGE_BUILD",
            status="SUCCEEDED_WITH_LIMITATIONS",
            stage_results=successful_stages("KNOWLEDGE_BUILD"),
            trace=execution_trace(),
            knowledge_snapshot_id="ks-1",
        )
