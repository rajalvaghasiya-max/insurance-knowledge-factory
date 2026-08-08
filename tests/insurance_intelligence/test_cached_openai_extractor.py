from __future__ import annotations

from dataclasses import replace

from insurance_intelligence.llm.cached_openai_extractor import CachedOpenAIExtractor
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
        output = {
            "components": [
                {
                    "component_id": "trigger",
                    "kind": "TRIGGER",
                    "reconstructed_attributes": [
                        {"name": "operator", "value": ">="},
                        {"name": "value", "value": 61},
                    ],
                    "confidence": 0.98,
                    "extractor_agreement": 0.0,
                    "unresolved_reasons": [],
                }
            ]
        }
        return (
            OpenAIStageTrace(
                trace_id=f"trace-{self.calls}",
                stage="EXTRACTION_OPENAI",
                model=kwargs["model"],
                prompt_version=kwargs["prompt_version"],
                request_id=kwargs["request_id"],
                provider_response_id=f"response-{self.calls}",
                latency_ms=10,
                canonical_output="{}",
            ),
            output,
        )


def _extract(extractor: CachedOpenAIExtractor, *, prompt="extract", rendered=None, schema=None):
    return extractor.extract(
        prompt=prompt,
        schema_name="component_semantic_extraction_openai",
        schema=schema or {"type": "object", "properties": {}},
        request_id="request-1",
        contract_payload='{"contract_id":"contract-1"}',
        rendered_components=rendered or [
            {"component_id": "trigger", "kind": "TRIGGER", "text": "Age 61 or older."}
        ],
        evidence_ids=("evidence-1",),
        rule_family_id="CONDITIONAL_COPAYMENT",
        rule_family_version="1.0",
        binding={"trigger": "trigger"},
        audience="customer",
        reading_level="plain_language",
        data_classification="PUBLIC",
    )


def test_first_extraction_calls_provider_and_stores_artifact(tmp_path):
    provider = _Provider()
    extractor = CachedOpenAIExtractor(provider, FilesystemGovernedArtifactStore(tmp_path))

    result = _extract(extractor)

    assert result.cache_hit is False
    assert provider.calls == 1


def test_identical_extraction_reuses_artifact_without_provider_call(tmp_path):
    provider = _Provider()
    extractor = CachedOpenAIExtractor(provider, FilesystemGovernedArtifactStore(tmp_path))

    first = _extract(extractor)
    second = _extract(extractor)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert provider.calls == 1
    assert first.cache_key == second.cache_key


def test_rendered_prompt_model_or_schema_drift_requires_fresh_provider_call(tmp_path):
    provider = _Provider()
    store = FilesystemGovernedArtifactStore(tmp_path)
    extractor = CachedOpenAIExtractor(provider, store)

    _extract(extractor)
    _extract(extractor, prompt="extract changed")
    _extract(
        extractor,
        rendered=[{"component_id": "trigger", "kind": "TRIGGER", "text": "At least age 61."}],
    )
    changed_model = CachedOpenAIExtractor(
        replace(provider, extractor_model="different-model"), store
    )
    _extract(changed_model)
    _extract(
        extractor,
        schema={"type": "object", "properties": {"components": {"type": "array"}}},
    )

    assert provider.calls == 5
