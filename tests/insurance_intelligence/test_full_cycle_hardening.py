from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from insurance_intelligence.orchestration.full_cycle_hardening import (
    FullCycleHardeningError,
    run_full_cycle_hardening_suite,
    validate_certification_result,
)
from insurance_intelligence.orchestration.full_cycle_certification import (
    FullKnowledgeToExplanationResult,
)


class _Section:
    status = "INCLUDED"
    text = "Valid section"


class _ResponseOutput:
    response_id = "response-1"
    direct_answer = "Yes."
    sections = (_Section(),)
    evidence_references = (object(),)


class _Response:
    product_reference = "star_health:star_comprehensive"
    topic = "conditional_copayment"
    knowledge_snapshot_id = "snapshot-1"
    response = _ResponseOutput()
    used_llm = False


class _Build:
    receipts = (object(),)
    publication_ids = ("pd-1",)


def _result(
    *,
    certification_id: str = "cert-1",
    snapshot_id: str = "snapshot-1",
    released_response_id: str = "response-1",
) -> FullKnowledgeToExplanationResult:
    return FullKnowledgeToExplanationResult(
        certification_id=certification_id,
        build_request_id="build-1",
        response_request_id="response-1",
        product_reference="star_health:star_comprehensive",
        topic="conditional_copayment",
        question="Will this apply?",
        knowledge_snapshot_id=snapshot_id,
        build=_Build(),  # type: ignore[arg-type]
        response=_Response(),  # type: ignore[arg-type]
        released_response_id=released_response_id,
        limitations=(),
        status="CERTIFIED",
    )


def _runner(**kwargs):
    context = kwargs.get("customer_context", {})
    name = context.get("trigger_status", "GENERAL")
    suffix = {
        "CONFIRMED": "yes",
        "NOT_TRIGGERED": "no",
        "UNRESOLVED": "clarify",
    }.get(name, "general")
    result = _result(
        certification_id=f"cert-{suffix}",
        released_response_id=f"response-{suffix}",
    )
    response_output = type(
        "ResponseOutput",
        (),
        {
            "response_id": f"response-{suffix}",
            "direct_answer": suffix,
            "sections": (_Section(),),
            "evidence_references": (object(),),
        },
    )()
    response = type(
        "Response",
        (),
        {
            "product_reference": "star_health:star_comprehensive",
            "topic": "conditional_copayment",
            "knowledge_snapshot_id": "snapshot-1",
            "response": response_output,
            "used_llm": False,
        },
    )()
    return replace(result, response=response)


def test_validate_accepts_certified_result() -> None:
    validate_certification_result(_result())


def test_validate_rejects_stale_snapshot() -> None:
    with pytest.raises(FullCycleHardeningError, match="stale"):
        validate_certification_result(
            _result(),
            expected_snapshot_id="snapshot-other",
        )


def test_validate_rejects_missing_publication_lineage() -> None:
    result = _result()
    build = type("Build", (), {"receipts": (object(),), "publication_ids": ()})()
    with pytest.raises(FullCycleHardeningError, match="publication lineage"):
        validate_certification_result(replace(result, build=build))


def test_validate_rejects_missing_evidence_lineage() -> None:
    result = _result()
    output = type(
        "Output",
        (),
        {
            "response_id": "response-1",
            "direct_answer": "Yes.",
            "sections": (_Section(),),
            "evidence_references": (),
        },
    )()
    response = type(
        "Response",
        (),
        {
            "product_reference": "star_health:star_comprehensive",
            "topic": "conditional_copayment",
            "knowledge_snapshot_id": "snapshot-1",
            "response": output,
            "used_llm": False,
        },
    )()
    with pytest.raises(FullCycleHardeningError, match="evidence lineage"):
        validate_certification_result(replace(result, response=response))


def test_validate_rejects_partial_release() -> None:
    with pytest.raises(FullCycleHardeningError, match="released response"):
        validate_certification_result(
            _result(released_response_id="response-other")
        )


def test_validate_rejects_llm_dependency() -> None:
    result = _result()
    response = type(
        "Response",
        (),
        {
            "product_reference": "star_health:star_comprehensive",
            "topic": "conditional_copayment",
            "knowledge_snapshot_id": "snapshot-1",
            "response": _ResponseOutput(),
            "used_llm": True,
        },
    )()
    with pytest.raises(FullCycleHardeningError, match="LLM-independent"):
        validate_certification_result(replace(result, response=response))


def test_validate_rejects_empty_released_section() -> None:
    result = _result()
    empty = type("Section", (), {"status": "INCLUDED", "text": "  "})()
    output = type(
        "Output",
        (),
        {
            "response_id": "response-1",
            "direct_answer": "Yes.",
            "sections": (empty,),
            "evidence_references": (object(),),
        },
    )()
    response = type(
        "Response",
        (),
        {
            "product_reference": "star_health:star_comprehensive",
            "topic": "conditional_copayment",
            "knowledge_snapshot_id": "snapshot-1",
            "response": output,
            "used_llm": False,
        },
    )()
    with pytest.raises(FullCycleHardeningError, match="empty"):
        validate_certification_result(replace(result, response=response))


def test_suite_runs_three_governed_cases(tmp_path: Path) -> None:
    report = run_full_cycle_hardening_suite(
        repository_root=tmp_path,
        build_request_id_prefix="build",
        response_request_id_prefix="response",
        question="Will this apply?",
        runner=_runner,
    )
    assert tuple(item.scenario_name for item in report.scenario_results) == (
        "CONFIRMED",
        "NOT_TRIGGERED",
        "UNRESOLVED",
    )
    assert report.passed_count == 3


def test_suite_is_deterministic(tmp_path: Path) -> None:
    report = run_full_cycle_hardening_suite(
        repository_root=tmp_path,
        build_request_id_prefix="build",
        response_request_id_prefix="response",
        question="Will this apply?",
        runner=_runner,
    )
    assert report.deterministic is True
    assert report.status == "CERTIFIED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("build_request_id_prefix", ""),
        ("response_request_id_prefix", ""),
        ("question", ""),
    ],
)
def test_suite_validates_required_text(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    values = {
        "repository_root": tmp_path,
        "build_request_id_prefix": "build",
        "response_request_id_prefix": "response",
        "question": "Will this apply?",
        "runner": _runner,
    }
    values[field] = value
    with pytest.raises(FullCycleHardeningError):
        run_full_cycle_hardening_suite(**values)


def test_suite_rejects_unsupported_topic(tmp_path: Path) -> None:
    with pytest.raises(FullCycleHardeningError, match="unsupported topic"):
        run_full_cycle_hardening_suite(
            repository_root=tmp_path,
            build_request_id_prefix="build",
            response_request_id_prefix="response",
            question="Explain OPD",
            topic="opd_cover",
            runner=_runner,
        )


def test_suite_rejects_unsupported_product(tmp_path: Path) -> None:
    with pytest.raises(FullCycleHardeningError, match="unsupported product"):
        run_full_cycle_hardening_suite(
            repository_root=tmp_path,
            build_request_id_prefix="build",
            response_request_id_prefix="response",
            question="Will this apply?",
            product_reference="other:product",
            runner=_runner,
        )


def test_suite_records_runner_failure_without_partial_release(tmp_path: Path) -> None:
    def failing_runner(**kwargs):
        context = kwargs.get("customer_context", {})
        if context.get("trigger_status") == "NOT_TRIGGERED":
            raise ValueError("broken lineage")
        return _runner(**kwargs)

    report = run_full_cycle_hardening_suite(
        repository_root=tmp_path,
        build_request_id_prefix="build",
        response_request_id_prefix="response",
        question="Will this apply?",
        runner=failing_runner,
    )
    assert report.status == "FAILED"
    failed = next(
        item for item in report.scenario_results
        if item.scenario_name == "NOT_TRIGGERED"
    )
    assert failed.released_response_id is None
