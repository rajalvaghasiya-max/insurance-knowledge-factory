"""OpenAI integration for component-locked rendering and semantic extraction.

Rendering and extraction are separate provider calls.  The renderer receives the
approved canonical contract and may return simplified text only.  The extractor
receives only rendered text plus component identities and reconstructs semantics
for deterministic MO-022G comparison.  Neither call can publish an explanation.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from time import monotonic
from typing import Mapping

import requests

from insurance_intelligence.contracts.semantic_fidelity import (
    ExplanationSemanticContract,
    FidelityRoutingPolicy,
    RuleFamilyCertification,
)
from insurance_intelligence.llm.component_locked import (
    ComponentLockedRenderRequest,
    build_component_locked_request,
)
from insurance_intelligence.llm.semantic_rendering_pipeline import (
    SemanticRenderingOutcome,
    evaluate_component_locked_rendering,
)


class OpenAIComponentLockedError(RuntimeError):
    """Raised when a component-locked OpenAI call cannot be safely completed."""


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpenAIComponentLockedError(f"{field_name} must be non-empty text")
    return value.strip()


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class OpenAIStageTrace:
    trace_id: str
    stage: str
    model: str
    prompt_version: str
    request_id: str
    provider_response_id: str
    latency_ms: int
    canonical_output: str


@dataclass(frozen=True)
class OpenAIComponentLockedResult:
    rendering_trace: OpenAIStageTrace
    extraction_trace: OpenAIStageTrace
    outcome: SemanticRenderingOutcome


def _renderer_schema(request: ComponentLockedRenderRequest) -> dict[str, object]:
    component_ids = [item.component_id for item in request.instructions]
    kinds = [item.kind.value for item in request.instructions]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["components"],
        "properties": {
            "components": {
                "type": "array",
                "minItems": len(component_ids),
                "maxItems": len(component_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["component_id", "kind", "text"],
                    "properties": {
                        "component_id": {"type": "string", "enum": component_ids},
                        "kind": {"type": "string", "enum": kinds},
                        "text": {"type": "string", "minLength": 1},
                    },
                },
            }
        },
    }


def _extractor_schema(request: ComponentLockedRenderRequest) -> dict[str, object]:
    component_ids = [item.component_id for item in request.instructions]
    kinds = [item.kind.value for item in request.instructions]
    semantic_value = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        ]
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["components"],
        "properties": {
            "components": {
                "type": "array",
                "minItems": len(component_ids),
                "maxItems": len(component_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "component_id", "kind", "reconstructed_attributes", "confidence",
                        "extractor_agreement", "unresolved_reasons"
                    ],
                    "properties": {
                        "component_id": {"type": "string", "enum": component_ids},
                        "kind": {"type": "string", "enum": kinds},
                        "reconstructed_attributes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["name", "value"],
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "value": semantic_value,
                                },
                            },
                        },
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "extractor_agreement": {"type": "number", "minimum": 0, "maximum": 1},
                        "unresolved_reasons": {
                            "type": "array", "items": {"type": "string"}, "uniqueItems": True
                        },
                    },
                },
            }
        },
    }


def _response_text(payload: object) -> tuple[str, str]:
    if not isinstance(payload, Mapping):
        raise OpenAIComponentLockedError("OpenAI response must be an object")
    response_id = _text(payload.get("id"), "response.id")
    output = payload.get("output")
    if not isinstance(output, list):
        raise OpenAIComponentLockedError("OpenAI response is missing output")
    texts: list[str] = []
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, Mapping) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
    if not texts:
        raise OpenAIComponentLockedError("OpenAI response contains no output_text")
    return response_id, "\n".join(texts)


@dataclass(frozen=True)
class OpenAIComponentLockedProvider:
    api_key: str
    renderer_model: str = "gpt-5-mini-2025-08-07"
    extractor_model: str = "gpt-5-mini-2025-08-07"
    endpoint: str = "https://api.openai.com/v1/responses"
    renderer_prompt_version: str = "component-locked-renderer-v1"
    extractor_prompt_version: str = "semantic-extractor-v1"
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        object.__setattr__(self, "api_key", _text(self.api_key, "api_key"))
        for field_name in (
            "renderer_model", "extractor_model", "endpoint",
            "renderer_prompt_version", "extractor_prompt_version"
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not self.endpoint.startswith("https://"):
            raise OpenAIComponentLockedError("endpoint must use HTTPS")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int):
            raise OpenAIComponentLockedError("timeout_seconds must be an integer")
        if self.timeout_seconds < 1:
            raise OpenAIComponentLockedError("timeout_seconds must be positive")

    @classmethod
    def from_environment(cls) -> "OpenAIComponentLockedProvider":
        return cls(api_key=os.environ.get("OPENAI_API_KEY", ""))

    def _call(
        self,
        *,
        model: str,
        prompt: str,
        schema_name: str,
        schema: Mapping[str, object],
        stage: str,
        prompt_version: str,
        request_id: str,
    ) -> tuple[OpenAIStageTrace, Mapping[str, object]]:
        body = {
            "model": model,
            "input": prompt,
            "store": False,
            "reasoning": {"effort": "low"},
            "max_output_tokens": 1800,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": dict(schema),
                }
            },
        }
        started = monotonic()
        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise OpenAIComponentLockedError(f"OpenAI {stage} request failed: {exc}") from exc
        latency_ms = int((monotonic() - started) * 1000)
        if response.status_code >= 400:
            message = response.text.strip()[:500] or f"HTTP {response.status_code}"
            raise OpenAIComponentLockedError(
                f"OpenAI {stage} returned HTTP {response.status_code}: {message}"
            )
        try:
            response_payload = response.json()
        except ValueError as exc:
            raise OpenAIComponentLockedError(f"OpenAI {stage} returned invalid JSON") from exc
        provider_response_id, output_text = _response_text(response_payload)
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise OpenAIComponentLockedError(
                f"OpenAI {stage} output is not valid structured JSON"
            ) from exc
        if not isinstance(parsed, Mapping):
            raise OpenAIComponentLockedError(f"OpenAI {stage} output must be an object")
        canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        trace = OpenAIStageTrace(
            trace_id=_stable_id("openai-stage", stage, request_id, provider_response_id, canonical),
            stage=stage,
            model=model,
            prompt_version=prompt_version,
            request_id=request_id,
            provider_response_id=provider_response_id,
            latency_ms=latency_ms,
            canonical_output=canonical,
        )
        return trace, parsed

    def evaluate(
        self,
        contract: ExplanationSemanticContract,
        *,
        audience: str,
        reading_level: str,
        policy: FidelityRoutingPolicy,
        certification: RuleFamilyCertification | None,
    ) -> OpenAIComponentLockedResult:
        request = build_component_locked_request(
            contract, audience=audience, reading_level=reading_level
        )
        render_prompt = (
            "Simplify wording only. Do not add, remove, infer, generalise, narrow, or change "
            "any fact or semantic relationship. Return each requested component exactly once.\n"
            f"REQUEST={request.canonical_payload}"
        )
        rendering_trace, rendered = self._call(
            model=self.renderer_model,
            prompt=render_prompt,
            schema_name="component_locked_rendering",
            schema=_renderer_schema(request),
            stage="RENDERING",
            prompt_version=self.renderer_prompt_version,
            request_id=request.request_id,
        )
        rendered_components = rendered.get("components")
        if not isinstance(rendered_components, list):
            raise OpenAIComponentLockedError("renderer output is missing components")
        extraction_input = {
            "contract_id": request.contract_id,
            "components": rendered_components,
            "allowed_component_ids": [item.component_id for item in request.instructions],
        }
        extraction_prompt = (
            "Reconstruct only the literal semantics expressed in each rendered component. "
            "Do not correct the text using outside knowledge and do not compare it with an expected answer. "
            "Mark ambiguity in unresolved_reasons and lower confidence.\n"
            f"INPUT={json.dumps(extraction_input, sort_keys=True, separators=(',', ':'))}"
        )
        extraction_trace, extracted = self._call(
            model=self.extractor_model,
            prompt=extraction_prompt,
            schema_name="component_semantic_extraction",
            schema=_extractor_schema(request),
            stage="EXTRACTION",
            prompt_version=self.extractor_prompt_version,
            request_id=request.request_id,
        )
        extracted_components = extracted.get("components")
        if not isinstance(extracted_components, list):
            raise OpenAIComponentLockedError("extractor output is missing components")
        rendered_by_id = {
            item.get("component_id"): item for item in rendered_components if isinstance(item, Mapping)
        }
        combined_components: list[dict[str, object]] = []
        for item in extracted_components:
            if not isinstance(item, Mapping):
                raise OpenAIComponentLockedError("extractor component must be an object")
            component_id = item.get("component_id")
            rendered_item = rendered_by_id.get(component_id)
            if not isinstance(rendered_item, Mapping):
                raise OpenAIComponentLockedError("extractor returned an unknown component")
            combined_components.append({
                "component_id": component_id,
                "kind": item.get("kind"),
                "text": rendered_item.get("text"),
                "reconstructed_attributes": item.get("reconstructed_attributes"),
                "confidence": item.get("confidence"),
                "extractor_ids": [self.extractor_prompt_version],
                "extractor_agreement": item.get("extractor_agreement"),
                "unresolved_reasons": item.get("unresolved_reasons"),
            })
        outcome = evaluate_component_locked_rendering(
            contract,
            request,
            {"components": combined_components},
            policy,
            certification,
        )
        return OpenAIComponentLockedResult(
            rendering_trace=rendering_trace,
            extraction_trace=extraction_trace,
            outcome=outcome,
        )
