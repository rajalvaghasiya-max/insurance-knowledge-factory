from dataclasses import FrozenInstanceError
import pytest

from insurance_intelligence.contracts.full_cycle import (
    build_failure_record,
    build_orchestration_request,
    build_product_scope,
    build_stage_output_reference,
    build_stage_result,
    build_trace_event,
)
from insurance_intelligence.orchestration.execution_state import (
    ExecutionStateError,
    build_execution_state,
    build_stage_checkpoint,
    can_publish,
    merge_resumed_execution,
    validate_resume,
)


def request():
    return build_orchestration_request(
        execution_id="exec-1",
        mode="KNOWLEDGE_BUILD",
        product_scope=build_product_scope(domain="health", insurer_id="star", product_id="comprehensive"),
    )


def output(stage, suffix="1"):
    return build_stage_output_reference(output_id=f"{stage}:{suffix}", output_type="receipt", content_digest=f"digest-{stage}-{suffix}")


def result(seq, status="SUCCEEDED", *, retryable=False, failure_kind="STAGE_ERROR"):
    stage = request().requested_stage_order[seq - 1]
    failure = None
    outputs = ()
    if status in {"SUCCEEDED", "SUCCEEDED_WITH_LIMITATIONS"}:
        outputs = (output(stage),)
    if status in {"FAILED", "BLOCKED"}:
        failure = build_failure_record(
            failure_id=f"f-{seq}", stage=stage,
            failure_kind=failure_kind if status == "FAILED" else "DEPENDENCY_BLOCKED",
            message="boom", retryable=retryable,
        )
    return build_stage_result(
        execution_id="exec-1", stage=stage, sequence=seq, status=status,
        outputs=outputs, failure=failure,
        limitations=("limited",) if status == "SUCCEEDED_WITH_LIMITATIONS" else (),
    )


def event(seq, stage, event_type="STAGE_COMPLETED"):
    return build_trace_event(event_id=f"e-{seq}", execution_id="exec-1", sequence=seq, event_type=event_type, stage=stage, message="ok")


def trace_for(results):
    return tuple(event(i, r.stage, "STAGE_FAILED" if r.status == "FAILED" else "STAGE_BLOCKED" if r.status == "BLOCKED" else "STAGE_COMPLETED") for i, r in enumerate(results, 1))


def test_checkpoint_is_deterministic_and_immutable():
    r = result(1); t = trace_for((r,))
    a = build_stage_checkpoint(result=r, trace=t); b = build_stage_checkpoint(result=r, trace=t)
    assert a == b and a.checkpoint_id.startswith("checkpoint:exec-1:1:")
    with pytest.raises(FrozenInstanceError): a.stage = "PARSING"


def test_checkpoint_rejects_failed_stage():
    r = result(1, "FAILED", retryable=True)
    with pytest.raises(ExecutionStateError): build_stage_checkpoint(result=r, trace=trace_for((r,)))


def test_checkpoint_requires_stage_trace():
    with pytest.raises(ExecutionStateError): build_stage_checkpoint(result=result(1), trace=())


def test_empty_state_starts_at_first_stage():
    s = build_execution_state(request=request(), completed_stage_results=(), trace=())
    assert s.last_validated_sequence == 0 and s.next_stage == "DISCOVERY" and not s.terminal


def test_success_prefix_creates_checkpoints():
    rs = (result(1), result(2, "SUCCEEDED_WITH_LIMITATIONS"))
    s = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    assert len(s.checkpoints) == 2 and s.next_stage == "SOURCE_REGISTRATION"


def test_not_required_and_skipped_are_validated():
    rs = (result(1, "NOT_REQUIRED"), result(2, "SKIPPED"))
    s = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    assert s.last_validated_sequence == 2


def test_retryable_failure_is_resumable_from_failed_stage():
    rs = (result(1), result(2, "FAILED", retryable=True))
    s = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    assert s.resumable and s.next_stage == "SOURCE_ACQUISITION"
    assert validate_resume(request=request(), state=s) == "SOURCE_ACQUISITION"


def test_stage_error_is_resumable_even_without_retry_flag():
    rs = (result(1), result(2, "FAILED"))
    assert build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs)).resumable


def test_identity_mismatch_failure_is_not_resumable():
    rs = (result(1), result(2, "FAILED", retryable=True, failure_kind="IDENTITY_MISMATCH"))
    s = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    assert not s.resumable and s.next_stage is None


def test_blocked_state_is_not_resumable():
    rs = (result(1, "FAILED", failure_kind="PUBLICATION_BLOCKED"), result(2, "BLOCKED"))
    s = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    assert not s.resumable


def test_complete_success_is_publishable():
    rs = tuple(result(i) for i in range(1, 11))
    s = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    assert s.terminal and can_publish(s)


def test_partial_success_is_not_publishable():
    rs = (result(1),)
    assert not can_publish(build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs)))

@pytest.mark.parametrize("mutation", ["wrong_exec", "wrong_sequence", "wrong_stage"])
def test_state_rejects_invalid_stage_prefix(mutation):
    r = result(1)
    if mutation == "wrong_exec":
        r = build_stage_result(execution_id="other", stage=r.stage, sequence=1, status="SUCCEEDED", outputs=(output(r.stage),))
    elif mutation == "wrong_sequence":
        r = build_stage_result(execution_id="exec-1", stage=r.stage, sequence=2, status="SUCCEEDED", outputs=(output(r.stage),))
    else:
        r = build_stage_result(execution_id="exec-1", stage="PARSING", sequence=1, status="SUCCEEDED", outputs=(output("PARSING"),))
    with pytest.raises(ExecutionStateError): build_execution_state(request=request(), completed_stage_results=(r,), trace=trace_for((r,)))


def test_state_rejects_nonterminal_stage():
    r = build_stage_result(execution_id="exec-1", stage="DISCOVERY", sequence=1, status="PENDING")
    with pytest.raises(ExecutionStateError): build_execution_state(request=request(), completed_stage_results=(r,), trace=())


def test_state_rejects_success_after_failure():
    rs = (result(1, "FAILED"), result(2))
    with pytest.raises(ExecutionStateError): build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))


def test_state_rejects_trace_identity_mismatch():
    r = result(1)
    bad = build_trace_event(event_id="e-1", execution_id="other", sequence=1, event_type="STAGE_COMPLETED", stage=r.stage, message="x")
    with pytest.raises(ExecutionStateError): build_execution_state(request=request(), completed_stage_results=(r,), trace=(bad,))


def test_state_rejects_trace_gap():
    r = result(1)
    bad = build_trace_event(event_id="e-2", execution_id="exec-1", sequence=2, event_type="STAGE_COMPLETED", stage=r.stage, message="x")
    with pytest.raises(ExecutionStateError): build_execution_state(request=request(), completed_stage_results=(r,), trace=(bad,))


def test_state_id_is_deterministic():
    rs = (result(1),)
    a = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    b = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    assert a.state_id == b.state_id


def test_validate_resume_rejects_different_execution():
    rs = (result(1), result(2, "FAILED")); s = build_execution_state(request=request(), completed_stage_results=rs, trace=trace_for(rs))
    other = build_orchestration_request(execution_id="other", mode="KNOWLEDGE_BUILD", product_scope=request().product_scope)
    with pytest.raises(ExecutionStateError): validate_resume(request=other, state=s)


def test_validate_resume_rejects_non_resumable_state():
    s = build_execution_state(request=request(), completed_stage_results=(result(1),), trace=trace_for((result(1),)))
    with pytest.raises(ExecutionStateError): validate_resume(request=request(), state=s)


def test_merge_resumed_execution_replaces_failed_suffix():
    prior_results = (result(1), result(2, "FAILED"))
    prior = build_execution_state(request=request(), completed_stage_results=prior_results, trace=trace_for(prior_results))
    resumed = (result(2), result(3))
    new_trace = (
        build_trace_event(event_id="e-3", execution_id="exec-1", sequence=3, event_type="STAGE_COMPLETED", stage=resumed[0].stage, message="retry ok"),
        build_trace_event(event_id="e-4", execution_id="exec-1", sequence=4, event_type="STAGE_COMPLETED", stage=resumed[1].stage, message="ok"),
    )
    merged = merge_resumed_execution(request=request(), prior_state=prior, resumed_stage_results=resumed, resumed_trace=new_trace)
    assert [r.status for r in merged.completed_stage_results] == ["SUCCEEDED", "SUCCEEDED", "SUCCEEDED"]
    assert merged.last_validated_sequence == 3


def test_merge_requires_resume_stage():
    prior_results = (result(1), result(2, "FAILED")); prior = build_execution_state(request=request(), completed_stage_results=prior_results, trace=trace_for(prior_results))
    with pytest.raises(ExecutionStateError): merge_resumed_execution(request=request(), prior_state=prior, resumed_stage_results=(result(3),), resumed_trace=())


def test_merge_rejects_trace_discontinuity():
    prior_results = (result(1), result(2, "FAILED")); prior = build_execution_state(request=request(), completed_stage_results=prior_results, trace=trace_for(prior_results))
    bad = build_trace_event(event_id="e-9", execution_id="exec-1", sequence=9, event_type="STAGE_COMPLETED", stage=result(2).stage, message="x")
    with pytest.raises(ExecutionStateError): merge_resumed_execution(request=request(), prior_state=prior, resumed_stage_results=(result(2),), resumed_trace=(bad,))


def test_execution_state_is_immutable():
    s = build_execution_state(request=request(), completed_stage_results=(), trace=())
    with pytest.raises(FrozenInstanceError): s.next_stage = "PARSING"
