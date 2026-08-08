from __future__ import annotations

from insurance_intelligence.llm.gemini_semantic_extractor import GeminiSemanticExtractor
from insurance_intelligence.llm.governed_artifact_store import FilesystemGovernedArtifactStore
from insurance_intelligence.llm.openai_component_locked import OpenAIComponentLockedProvider
from insurance_intelligence.llm.openai_gemini_cross_provider import OpenAIGeminiCrossProvider
from scripts.run_mo_022g_star_copay_live import build_live_policy, build_star_copay_contract
from tests.insurance_intelligence.test_openai_gemini_cross_provider import (
    _GeminiResponse,
    _Response,
    _extracted,
    _rendered,
)


def test_identical_cross_provider_evaluation_replays_with_zero_provider_calls(monkeypatch, tmp_path):
    counts = {"openai": 0, "gemini": 0}
    openai_responses = iter(
        [
            _Response("render-1", _rendered()),
            _Response("extract-1", _extracted()),
        ]
    )

    def post(url, *args, **kwargs):
        if "generativelanguage.googleapis.com" in url:
            counts["gemini"] += 1
            return _GeminiResponse(_extracted())
        if "api.openai.com" in url:
            counts["openai"] += 1
            return next(openai_responses)
        raise AssertionError(f"unexpected provider URL: {url}")

    monkeypatch.setattr(
        "insurance_intelligence.llm.openai_component_locked.requests.post",
        post,
    )

    provider = OpenAIGeminiCrossProvider(
        openai=OpenAIComponentLockedProvider(api_key="openai-test"),
        gemini=GeminiSemanticExtractor(api_key="gemini-test"),
        renderer_store=FilesystemGovernedArtifactStore(tmp_path),
    )
    arguments = {
        "audience": "customer",
        "reading_level": "plain_language",
        "policy": build_live_policy(),
        "certification": None,
        "data_classification": "PUBLIC",
        "cache_rule_family_version": "1.0",
        "cache_binding": {
            "family_id": "CONDITIONAL_COPAYMENT",
            "family_version": "1.0",
            "contract_id": "contract-star-comprehensive-conditional-copay-v1",
            "component_roles": [
                ["trigger", "entry-age-trigger"],
                ["effect", "copay-effect"],
                ["exception", "continuous-renewal-exception"],
                ["scope", "applicability-scope"],
            ],
        },
    }

    first = provider.evaluate(build_star_copay_contract(), **arguments)
    counts_after_first = dict(counts)
    second = provider.evaluate(build_star_copay_contract(), **arguments)

    assert first.renderer_cache_hit is False
    assert first.openai_extractor_cache_hit is False
    assert first.gemini_extractor_cache_hit is False
    assert counts_after_first == {"openai": 2, "gemini": 1}

    assert second.renderer_cache_hit is True
    assert second.openai_extractor_cache_hit is True
    assert second.gemini_extractor_cache_hit is True
    assert first.renderer_cache_key == second.renderer_cache_key
    assert first.openai_extractor_cache_key == second.openai_extractor_cache_key
    assert first.gemini_extractor_cache_key == second.gemini_extractor_cache_key
    assert second.artifact_store_root == str(tmp_path)
    assert counts == counts_after_first
    assert all(item.agreed for item in first.agreements)
    assert all(item.agreed for item in second.agreements)
