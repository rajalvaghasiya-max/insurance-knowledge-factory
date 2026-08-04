from __future__ import annotations

from insurance_intelligence.llm.cached_openai_renderer import CachedOpenAIRenderer
from insurance_intelligence.llm.governed_artifact_store import FilesystemGovernedArtifactStore
from insurance_intelligence.llm.openai_component_locked import (
    OpenAIComponentLockedProvider,
    OpenAIStageTrace,
)


class _Provider(OpenAIComponentLockedProvider):
    def __init__(self):
        super().__init__(api_key="test-key")
        object.__setattr__(self, "calls", 0)

    def _call(self, **kwargs):
        object.__setattr__(self, "calls", self.calls + 1)
        output = {"components": [{"component_id": "trigger", "kind": "TRIGGER", "text": "Age 61 or older."}]}
        return (
            OpenAIStageTrace(
                trace_id=f"trace-{self.calls}",
                stage="RENDERING",
                model=kwargs["model"],
                prompt_version=kwargs["prompt_version"],
                request_id=kwargs["request_id"],
                provider_response_id=f"response-{self.calls}",
                latency_ms=10,
                canonical_output='{"components":[{"component_id":"trigger","kind":"TRIGGER","text":"Age 61 or older."}]}',
            ),
            output,
        )


def _render(renderer: CachedOpenAIRenderer, *, prompt: str = "render", schema=None):
    return renderer.render(
        prompt=prompt,
        schema_name="component_locked_rendering",
        schema=schema or {"type": "object", "properties": {}},
        request_id="request-1",
        contract_payload='{"contract_id":"contract-1"}',
        evidence_ids=("evidence-1",),
        rule_family_id="CONDITIONAL_COPAYMENT",
        rule_family_version="1.0",
        binding={"trigger": "trigger"},
        audience="customer",
        reading_level="plain_language",
        data_classification="PUBLIC",
    )


def test_first_request_calls_provider_and_stores_artifact(tmp_path):
    provider = _Provider()
    renderer = CachedOpenAIRenderer(provider, FilesystemGovernedArtifactStore(tmp_path))

    result = _render(renderer)

    assert result.cache_hit is False
    assert provider.calls == 1
    assert result.output["components"][0]["component_id"] == "trigger"


def test_identical_request_reuses_artifact_without_provider_call(tmp_path):
    provider = _Provider()
    renderer = CachedOpenAIRenderer(provider, FilesystemGovernedArtifactStore(tmp_path))

    first = _render(renderer)
    second = _render(renderer)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert provider.calls == 1
    assert second.trace.provider_response_id == first.trace.provider_response_id


def test_prompt_model_or_schema_drift_requires_fresh_provider_call(tmp_path):
    provider = _Provider()
    store = FilesystemGovernedArtifactStore(tmp_path)
    renderer = CachedOpenAIRenderer(provider, store)

    _render(renderer)
    _render(renderer, prompt="render changed")
    object.__setattr__(provider, "renderer_model", "different-model")
    _render(renderer, prompt="render changed")
    object.__setattr__(provider, "renderer_model", "gpt-5-mini-2025-08-07")
    _render(
        renderer,
        schema={"type": "object", "properties": {"components": {"type": "array"}}},
    )

    assert provider.calls == 4
