from __future__ import annotations

from dataclasses import fields

from insurance_intelligence.orchestration.real_response_prefix import (
    RealResponsePrefixDependencies,
)


def test_real_response_dependencies_expose_governed_education_lookup_handoff() -> None:
    names = {item.name for item in fields(RealResponsePrefixDependencies)}

    assert "concept_registry" in names
    assert "education_publication_lookup" in names
