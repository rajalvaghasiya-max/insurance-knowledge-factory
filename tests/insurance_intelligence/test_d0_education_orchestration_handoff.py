from __future__ import annotations

import inspect

from insurance_intelligence.orchestration.real_response_explanation import (
    build_real_response_explanation_adapters,
)


def test_real_response_explanation_exposes_generic_education_publication_lookup() -> None:
    parameters = inspect.signature(
        build_real_response_explanation_adapters
    ).parameters

    assert "education_publication_lookup" in parameters
    assert parameters["education_publication_lookup"].default is None
