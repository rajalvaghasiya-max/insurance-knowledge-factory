"""Generic extension of the real response path through the canonical rendering stage.

When an orchestration request disables LLM rendering, the existing intelligence
adapter runtime marks LLM_RENDERING as NOT_REQUIRED before invoking the supplied
rendering capability. This module only composes that governed stage; it does not
implement or bypass rendering policy itself.
"""
from __future__ import annotations

from insurance_intelligence.orchestration.intelligence_adapters import (
    IntelligenceStageCapability,
    build_intelligence_stage_adapter,
)
from insurance_intelligence.orchestration.real_response_assembly import (
    build_real_response_assembly_adapters,
)
from insurance_intelligence.orchestration.real_response_prefix import (
    RealResponsePrefixDependencies,
    RealResponsePrefixError,
)
from insurance_intelligence.explanation.registry import ExplanationStyleRegistry, TerminologyRegistry
from insurance_intelligence.response.registry import ResponseFormatRegistry


def build_real_response_rendering_adapters(
    *,
    dependencies: RealResponsePrefixDependencies,
    style_registry: ExplanationStyleRegistry,
    response_registry: ResponseFormatRegistry,
    rendering_capability: IntelligenceStageCapability,
    terminology_registry: TerminologyRegistry | None = None,
    response_format: str = "STANDARD",
):
    """Build the proven real path plus canonical LLM_RENDERING composition."""
    if not callable(rendering_capability):
        raise RealResponsePrefixError("rendering_capability must be callable")

    prior = build_real_response_assembly_adapters(
        dependencies=dependencies,
        style_registry=style_registry,
        response_registry=response_registry,
        terminology_registry=terminology_registry,
        response_format=response_format,
    )
    return prior + (
        build_intelligence_stage_adapter(
            stage="LLM_RENDERING",
            capability=rendering_capability,
        ),
    )


__all__ = ["build_real_response_rendering_adapters"]
