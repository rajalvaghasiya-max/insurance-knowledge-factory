from __future__ import annotations

import inspect

from insurance_intelligence.orchestration.real_response_reasoning import (
    build_real_response_reasoning_adapters,
)


def test_reasoning_stage_does_not_bypass_canonical_context_building_output() -> None:
    """Freeze the canonical handoff invariant before any runtime repair.

    CONTEXT_BUILDING is a canonical governed stage. REASONING must consume an
    approved projection of that stage's resolved context rather than rereading
    raw request.customer_context directly.
    """

    source = inspect.getsource(build_real_response_reasoning_adapters)

    assert "request.customer_context" not in source
    assert "CONTEXT_BUILDING" in source
