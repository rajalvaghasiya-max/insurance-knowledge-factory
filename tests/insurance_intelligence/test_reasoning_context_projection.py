from __future__ import annotations

import inspect

import pytest

from insurance_intelligence.context.reasoning_projection import (
    ReasoningContextProjectionError,
    project_reasoning_context,
)
from insurance_intelligence.contracts.context import (
    build_output,
    build_resolved_context_item,
)
from insurance_intelligence.orchestration.real_response_reasoning import (
    build_real_response_reasoning_adapters,
)


def _item(*, key: str, value: str, provenance: str = "USER_PROVIDED", status: str = "ACTIVE"):
    return build_resolved_context_item(
        key=key,
        value=value,
        category="SCENARIO",
        provenance=provenance,
        source_reference="test",
        confidence=1.0,
        status=status,
        materiality="high",
    )


def _context(*items):
    return build_output(
        request_id="request:context-projection",
        answerability="ANSWERABLE",
        context_completeness=1.0,
        resolved_context=items,
        classification_basis=("user_provided",),
    )


def test_reasoning_stage_consumes_canonical_context_not_raw_request_context() -> None:
    source = inspect.getsource(build_real_response_reasoning_adapters)

    assert "request.customer_context" not in source
    assert "CONTEXT_BUILDING" in source
    assert "project_reasoning_context(context)" in source


def test_projection_restores_only_registered_boolean_control() -> None:
    projected = project_reasoning_context(
        _context(
            _item(key="case_specific_applicability", value="True"),
            _item(key="hospitalization_date", value="2026-09-14"),
        )
    )

    assert projected["case_specific_applicability"] is True
    assert projected["hospitalization_date"] == "2026-09-14"


def test_projection_rejects_invalid_boolean_control() -> None:
    with pytest.raises(ReasoningContextProjectionError, match="canonical boolean"):
        project_reasoning_context(_context(_item(key="case_specific_applicability", value="yes")))


def test_projection_bounds_copayment_trigger_status() -> None:
    projected = project_reasoning_context(
        _context(_item(key="conditional_copayment_trigger_status", value="not_triggered"))
    )
    assert projected["conditional_copayment_trigger_status"] == "NOT_TRIGGERED"

    with pytest.raises(ReasoningContextProjectionError, match="must be one of"):
        project_reasoning_context(
            _context(_item(key="conditional_copayment_trigger_status", value="probably"))
        )


def test_projection_excludes_untrusted_or_inactive_context() -> None:
    projected = project_reasoning_context(
        _context(
            _item(key="trusted", value="yes"),
            _item(key="unverified", value="x", provenance="UNVERIFIED"),
            _item(key="stale", value="x", provenance="STALE"),
            _item(key="superseded", value="x", status="SUPERSEDED"),
        )
    )
    assert projected == {"trusted": "yes"}


def test_projection_fails_closed_on_duplicate_active_key() -> None:
    with pytest.raises(ReasoningContextProjectionError, match="duplicate active"):
        project_reasoning_context(
            _context(
                _item(key="scenario_context", value="first"),
                _item(key="scenario_context", value="second"),
            )
        )
