"""Governed Gemini semantic extractor for public/synthetic certification cases."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from time import monotonic
from typing import Mapping

import requests


class GeminiSemanticExtractorError(RuntimeError):
    """Raised when Gemini extraction cannot be completed safely."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeminiSemanticExtractorError(f"{field} must be non-empty text")
    return value.strip()


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


_GEMINI_SCHEMA_KEYS = {
    "type",
    "format",
    "description",
    "nullable",
    "enum",
    "items",
    "properties",
    "required",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "anyOf",
    "propertyOrdering",
}


def compile_gemini_schema(value: object) -> object:
    """Compile provider-neutral JSON Schema into Gemini's supported subset.

    Gemini's REST Schema is not full JSON Schema. Unsupported control keywords
    such as ``additionalProperties`` are intentionally removed here; strictness
    remains enforced by local parsing and the deterministic canonical gate.
    """
    if isinstance(value, Mapping):
        compiled: dict[str, object] = {}
        for key, item in value.items():
            if key not in _GEMINI_SCHEMA_KEYS:
                continue
            if key == "properties" and isinstance(item, Mapping):
                compiled[key] = {
                    str(name): compile_gemini_schema(schema)
                    for name, schema in item.items()
                }
            else:
                compiled[key] = compile_gemini_schema(item)
        return compiled
    if isinstance(value, list):
        return [compile_gemini_schema(item) for item in value]
    if isinstance(value, tuple):
        return [compile_gemini_schema(item) for item in value]
    return value


@dataclass(frozen=True)
class GeminiExtractionTrace:
    trace_id: str
    provider: str
    model: str
    prompt_version: str
    request_id: str
    latency_ms: int
    canonical_output: str


@dataclass(frozen=True)
class GeminiSemanticExtractor:
    api_key: str
    model: str = "gemini-2.5-flash-lite"
    endpoint_base: str = "https://generativelanguage.googleapis.com/v1beta/models"
    prompt_version: str = "semantic-extractor-gemini-v1"
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        object.__setattr__(self, "api_key", _text(self.api_key, "api_key"))
        object.__setattr__(self, "model", _text(self.model, "model"))
        object.__setattr__(self, "endpoint_base", _text(self.endpoint_base, "endpoint_base"))
        object.__setattr__(self, "prompt_version", _text(self.prompt_version, "prompt_version"))
        if not self.endpoint_base.startswith("https://"):
            raise GeminiSemanticExtractorError("endpoint_base must use HTTPS")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int):
            raise GeminiSemanticExtractorError("timeout_seconds must be an integer")
        if self.timeout_seconds < 1:
            raise GeminiSemanticExtractorError("timeout_seconds must be positive")

    @classmethod
    def from_environment(cls) -> "GeminiSemanticExtractor":
        return cls(api_key=os.environ.get("GEMINI_API_KEY", ""))

    def extract(
        self,
        *,
        prompt: str,
        schema: Mapping[str, object],
        request_id: str,
        data_classification: str,
    ) -> tuple[GeminiExtractionTrace, Mapping[str, object]]:
        if data_classification not in {"PUBLIC", "SYNTHETIC"}:
            raise GeminiSemanticExtractorError(
                "Gemini free-tier extraction is restricted to PUBLIC or SYNTHETIC data"
            )
        prompt = _text(prompt, "prompt")
        request_id = _text(request_id, "request_id")
        endpoint = f"{self.endpoint_base}/{self.model}:generateContent"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": compile_gemini_schema(schema),
                "temperature": 0,
            },
        }
        started = monotonic()
        try:
            response = requests.post(
                endpoint,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                json=body,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise GeminiSemanticExtractorError(f"Gemini request failed: {exc}") from exc
        latency_ms = int((monotonic() - started) * 1000)
        if response.status_code >= 400:
            raise GeminiSemanticExtractorError(
                f"Gemini returned HTTP {response.status_code}: {response.text[:500]}"
            )
        payload = response.json()
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiSemanticExtractorError("Gemini response contains no structured text") from exc
        try:
            parsed = json.loads(_text(text, "response.text"))
        except json.JSONDecodeError as exc:
            raise GeminiSemanticExtractorError("Gemini structured output is not valid JSON") from exc
        if not isinstance(parsed, Mapping):
            raise GeminiSemanticExtractorError("Gemini structured output must be an object")
        canonical_output = json.dumps(
            parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return (
            GeminiExtractionTrace(
                trace_id=_stable_id("gemini-stage", request_id, canonical_output),
                provider="google",
                model=self.model,
                prompt_version=self.prompt_version,
                request_id=request_id,
                latency_ms=latency_ms,
                canonical_output=canonical_output,
            ),
            parsed,
        )


__all__ = [
    "GeminiExtractionTrace",
    "GeminiSemanticExtractor",
    "GeminiSemanticExtractorError",
    "compile_gemini_schema",
]
