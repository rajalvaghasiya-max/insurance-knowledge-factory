from __future__ import annotations

from insurance_intelligence.llm.cached_gemini_extractor import CachedGeminiExtractor
from insurance_intelligence.llm.gemini_semantic_extractor import (
    GeminiExtractionTrace,
    GeminiSemanticExtractor,
)
from insurance_intelligence.llm.governed_artifact_store import FilesystemGovernedArtifactStore


class _Provider(GeminiSemanticExtractor):
    def __init__(self, *, model: str = "gemini-test-model"):
        super().__init__(api_key="test-key", model=model)
        object.__setattr__(self, "calls", 0)

    def extract(self, **kwargs):
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
            GeminiExtractionTrace(
                trace_id=f"trace-{self.calls}",
                provider="google",
                model=self.model,
                prompt_version=self.prompt_version,
                request_id=kwargs["request_id"],
                latency_ms=10,
                canonical_output="{}",
            ),
            output,
        )


def _extract(extractor: CachedGeminiExtractor, *, prompt="extract", rendered=None, schema=None):
    return extractor.extract(
        prompt=prompt,
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
    extractor = CachedGeminiExtractor(provider, FilesystemGovernedArtifactStore(tmp_path))

    result = _extract(extractor)

    assert result.cache_hit is False
    assert provider.calls == 1


def test_identical_extraction_reuses_artifact_without_provider_call(tmp_path):
    provider = _Provider()
    extractor = CachedGeminiExtractor(provider, FilesystemGovernedArtifactStore(tmp_path))

    first = _extract(extractor)
    second = _extract(extractor)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert provider.calls == 1
    assert first.cache_key == second.cache_key


def test_rendered_prompt_model_or_schema_drift_requires_fresh_provider_call(tmp_path):
    provider = _Provider()
    store = FilesystemGovernedArtifactStore(tmp_path)
    extractor = CachedGeminiExtractor(provider, store)

    _extract(extractor)
    _extract(extractor, prompt="extract changed")
    _extract(
        extractor,
        rendered=[{"component_id": "trigger", "kind": "TRIGGER", "text": "At least age 61."}],
    )
    changed_provider = _Provider(model="different-model")
    _extract(CachedGeminiExtractor(changed_provider, store))
    _extract(
        extractor,
        schema={"type": "object", "properties": {"components": {"type": "array"}}},
    )

    assert provider.calls == 4
    assert changed_provider.calls == 1
