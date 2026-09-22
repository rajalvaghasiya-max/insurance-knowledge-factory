from __future__ import annotations

import inspect

from insurance_intelligence.orchestration.real_response_assembly import (
    build_real_response_assembly_adapters,
)
from insurance_intelligence.orchestration.real_response_rendering import (
    build_real_response_rendering_adapters,
)


def test_real_response_assembly_exposes_education_lookup() -> None:
    parameters = inspect.signature(build_real_response_assembly_adapters).parameters
    assert "education_publication_lookup" in parameters
    assert parameters["education_publication_lookup"].default is None


def test_real_response_rendering_exposes_education_lookup() -> None:
    parameters = inspect.signature(build_real_response_rendering_adapters).parameters
    assert "education_publication_lookup" in parameters
    assert parameters["education_publication_lookup"].default is None
