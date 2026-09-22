from __future__ import annotations

import inspect

from insurance_intelligence.orchestration.real_response_explanation import (
    build_real_response_explanation_adapters,
)


def test_real_response_explanation_accepts_generic_education_publication_lookup() -> None:
    """The real D0 path must be able to receive published education generically."""
    parameters = inspect.signature(
        build_real_response_explanation_adapters
    ).parameters

    assert "education_publication_lookup" in parameters, (
        "published education is integrated into explanation/response contracts but "
        "the real orchestration path has no lookup/handoff for it"
    )
