from __future__ import annotations

import json

import pytest

from insurance_intelligence.llm.gemini_semantic_extractor import (
    GeminiSemanticExtractor,
    GeminiSemanticExtractorError,
    compile_gemini_schema,
)


class _Response:
    status_code = 200
    text = ""

    def json(self):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps({"components": [{"component_id": "x"}]})}
                        ]
                    }
                }
            ]
        }


def test_gemini_extractor_returns_governed_trace(monkeypatch):
    captured = {}

    def _post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr(
        "insurance_intelligence.llm.gemini_semantic_extractor.requests.post",
        _post,
    )
    extractor = GeminiSemanticExtractor(api_key="test-key")
    trace, output = extractor.extract(
        prompt="extract",
        schema={"type": "object"},
        request_id="request-1",
        data_classification="PUBLIC",
    )
    assert output == {"components": [{"component_id": "x"}]}
    assert trace.provider == "google"
    assert trace.model == "gemini-2.5-flash-lite"
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_compile_gemini_schema_removes_unsupported_keywords_recursively():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "components": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "value": {
                            "anyOf": [
                                {"type": "string"},
                                {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {"name": {"type": "string"}},
                                    },
                                },
                            ]
                        }
                    },
                    "required": ["value"],
                },
            }
        },
        "$schema": "https://json-schema.org/draft/2020-12/schema",
    }

    compiled = compile_gemini_schema(schema)
    encoded = json.dumps(compiled)

    assert "additionalProperties" not in encoded
    assert "$schema" not in encoded
    assert compiled["properties"]["components"]["items"]["required"] == ["value"]
    assert compiled["properties"]["components"]["items"]["properties"]["value"]["anyOf"][1]["items"]["properties"]["name"] == {"type": "string"}


def test_gemini_extractor_rejects_customer_data(monkeypatch):
    monkeypatch.setattr(
        "insurance_intelligence.llm.gemini_semantic_extractor.requests.post",
        lambda *args, **kwargs: pytest.fail("provider must not be called"),
    )
    extractor = GeminiSemanticExtractor(api_key="test-key")
    with pytest.raises(GeminiSemanticExtractorError, match="PUBLIC or SYNTHETIC"):
        extractor.extract(
            prompt="extract",
            schema={"type": "object"},
            request_id="request-1",
            data_classification="CUSTOMER_CONFIDENTIAL",
        )
