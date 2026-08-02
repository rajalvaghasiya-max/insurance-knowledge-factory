"""Component-locked rendering and semantic reconstruction for MO-022G.2.

The renderer may change wording only.  Every canonical semantic component must be
returned exactly once with a structured semantic reconstruction that is compared
by the deterministic MO-022G gate before publication.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping

from insurance_intelligence.contracts.semantic_fidelity import (
    ExplanationSemanticContract,
    ReconstructedSemanticComponent,
    SemanticAttribute,
    SemanticKind,
)


class ComponentLockedRenderingError(ValueError):
    """Raised when a component-locked rendering violates a hard invariant."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComponentLockedRenderingError(f"{field_name} must be non-empty text")
    return value.strip()


def _score(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ComponentLockedRenderingError(f"{field_name} must be numeric")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise ComponentLockedRenderingError(f"{field_name} must be between 0 and 1")
    return result


@dataclass(frozen=True)
class ComponentRenderInstruction:
    component_id: str
    kind: SemanticKind
    attributes: tuple[SemanticAttribute, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ComponentLockedRenderRequest:
    request_id: str
    contract_id: str
    contract_version: str
    rule_family: str
    audience: str
    reading_level: str
    instructions: tuple[ComponentRenderInstruction, ...]
    prohibited_operations: tuple[str, ...]
    canonical_payload: str


@dataclass(frozen=True)
class RenderedSemanticComponent:
    component_id: str
    kind: SemanticKind
    text: str
    reconstructed_attributes: tuple[SemanticAttribute, ...]
    confidence: float
    extractor_ids: tuple[str, ...]
    extractor_agreement: float
    unresolved_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParsedComponentLockedOutput:
    parse_id: str
    request_id: str
    rendered_components: tuple[RenderedSemanticComponent, ...]
    canonical_payload: str


@dataclass(frozen=True)
class VerifiedExplanation:
    explanation_id: str
    contract_id: str
    component_texts: tuple[tuple[str, str], ...]
    combined_text: str


def build_component_locked_request(
    contract: ExplanationSemanticContract,
    *,
    audience: str,
    reading_level: str,
    request_id: str | None = None,
) -> ComponentLockedRenderRequest:
    """Build a provider-neutral request with one immutable slot per component."""
    if not isinstance(contract, ExplanationSemanticContract):
        raise TypeError("contract must be an ExplanationSemanticContract")
    resolved_audience = _text(audience, "audience")
    resolved_reading_level = _text(reading_level, "reading_level")
    instructions = tuple(
        ComponentRenderInstruction(
            component_id=item.component_id,
            kind=item.kind,
            attributes=item.attributes,
            evidence_ids=item.evidence_ids,
        )
        for item in contract.components
    )
    payload = {
        "contract_id": contract.contract_id,
        "contract_version": contract.contract_version,
        "rule_family": contract.rule_family,
        "audience": resolved_audience,
        "reading_level": resolved_reading_level,
        "instructions": [
            {
                "component_id": item.component_id,
                "kind": item.kind.value,
                "attributes": [
                    {"name": attribute.name, "value": attribute.value}
                    for attribute in item.attributes
                ],
                "evidence_ids": list(item.evidence_ids),
            }
            for item in instructions
        ],
        "prohibited_operations": list(contract.prohibited_operations),
        "output_rule": (
            "Return every component exactly once. Simplify wording only. "
            "Do not add, omit, infer, generalise, narrow, or change semantics."
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    resolved_id = request_id or _stable_id("component-render-request", canonical)
    return ComponentLockedRenderRequest(
        request_id=resolved_id,
        contract_id=contract.contract_id,
        contract_version=contract.contract_version,
        rule_family=contract.rule_family,
        audience=resolved_audience,
        reading_level=resolved_reading_level,
        instructions=instructions,
        prohibited_operations=contract.prohibited_operations,
        canonical_payload=canonical,
    )


def _semantic_value(value: object, field_name: str) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return _text(value, field_name) if isinstance(value, str) else value
    if isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value):
        result = tuple(item.strip() for item in value)
        if len(result) != len(set(result)):
            raise ComponentLockedRenderingError(f"{field_name} must not contain duplicates")
        return result
    raise ComponentLockedRenderingError(f"{field_name} has an unsupported semantic value")


def _attributes(value: object, field_name: str) -> tuple[SemanticAttribute, ...]:
    if not isinstance(value, list):
        raise ComponentLockedRenderingError(f"{field_name} must be a list")
    result: list[SemanticAttribute] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or set(item) != {"name", "value"}:
            raise ComponentLockedRenderingError(
                f"{field_name}[{index}] must contain only name and value"
            )
        result.append(
            SemanticAttribute(
                name=_text(item["name"], f"{field_name}[{index}].name"),
                value=_semantic_value(item["value"], f"{field_name}[{index}].value"),
            )
        )
    names = tuple(item.name for item in result)
    if len(names) != len(set(names)):
        raise ComponentLockedRenderingError(f"{field_name} attribute names must be unique")
    return tuple(sorted(result))


def _string_tuple(value: object, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ComponentLockedRenderingError(f"{field_name} must be a list")
    result = tuple(_text(item, field_name) for item in value)
    if not allow_empty and not result:
        raise ComponentLockedRenderingError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise ComponentLockedRenderingError(f"{field_name} must not contain duplicates")
    return result


def parse_component_locked_output(
    raw_output: str | Mapping[str, object],
    request: ComponentLockedRenderRequest,
) -> ParsedComponentLockedOutput:
    """Parse exact component coverage and structured reconstructed semantics."""
    if isinstance(raw_output, str):
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise ComponentLockedRenderingError("provider output is not valid JSON") from exc
    elif isinstance(raw_output, Mapping):
        payload = dict(raw_output)
    else:
        raise ComponentLockedRenderingError("provider output must be JSON text or a mapping")

    if not isinstance(payload, dict) or set(payload) != {"components"}:
        raise ComponentLockedRenderingError("provider output must contain only components")
    raw_components = payload["components"]
    if not isinstance(raw_components, list) or not raw_components:
        raise ComponentLockedRenderingError("components must be a non-empty list")

    required = {
        "component_id",
        "kind",
        "text",
        "reconstructed_attributes",
        "confidence",
        "extractor_ids",
        "extractor_agreement",
        "unresolved_reasons",
    }
    expected = {item.component_id: item for item in request.instructions}
    parsed: list[RenderedSemanticComponent] = []
    for index, item in enumerate(raw_components):
        if not isinstance(item, Mapping) or set(item) != required:
            raise ComponentLockedRenderingError(f"components[{index}] has invalid fields")
        component_id = _text(item["component_id"], f"components[{index}].component_id")
        if component_id not in expected:
            raise ComponentLockedRenderingError("provider returned an unknown component_id")
        try:
            kind = SemanticKind(_text(item["kind"], f"components[{index}].kind"))
        except ValueError as exc:
            raise ComponentLockedRenderingError("provider returned an invalid semantic kind") from exc
        parsed.append(
            RenderedSemanticComponent(
                component_id=component_id,
                kind=kind,
                text=_text(item["text"], f"components[{index}].text"),
                reconstructed_attributes=_attributes(
                    item["reconstructed_attributes"],
                    f"components[{index}].reconstructed_attributes",
                ),
                confidence=_score(item["confidence"], f"components[{index}].confidence"),
                extractor_ids=_string_tuple(
                    item["extractor_ids"], f"components[{index}].extractor_ids", allow_empty=False
                ),
                extractor_agreement=_score(
                    item["extractor_agreement"],
                    f"components[{index}].extractor_agreement",
                ),
                unresolved_reasons=_string_tuple(
                    item["unresolved_reasons"], f"components[{index}].unresolved_reasons"
                ),
            )
        )

    ids = tuple(item.component_id for item in parsed)
    if len(ids) != len(set(ids)):
        raise ComponentLockedRenderingError("component_id values must be unique")
    if set(ids) != set(expected):
        raise ComponentLockedRenderingError("provider output must exactly cover requested components")

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    ordered = tuple(sorted(parsed, key=lambda item: tuple(expected).index(item.component_id)))
    return ParsedComponentLockedOutput(
        parse_id=_stable_id("component-render-parse", request.request_id, canonical),
        request_id=request.request_id,
        rendered_components=ordered,
        canonical_payload=canonical,
    )


def reconstruct_semantics(
    parsed: ParsedComponentLockedOutput,
) -> tuple[ReconstructedSemanticComponent, ...]:
    """Convert parsed provider output into the canonical comparator input."""
    return tuple(
        ReconstructedSemanticComponent(
            component_id=item.component_id,
            kind=item.kind,
            attributes=item.reconstructed_attributes,
            confidence=item.confidence,
            extractor_ids=item.extractor_ids,
            extractor_agreement=item.extractor_agreement,
            unresolved_reasons=item.unresolved_reasons,
        )
        for item in parsed.rendered_components
    )


def assemble_verified_explanation(
    contract: ExplanationSemanticContract,
    parsed: ParsedComponentLockedOutput,
    *,
    explanation_id: str | None = None,
) -> VerifiedExplanation:
    """Deterministically assemble text after semantic approval has been obtained."""
    expected_ids = tuple(item.component_id for item in contract.components)
    rendered = {item.component_id: item.text for item in parsed.rendered_components}
    if set(rendered) != set(expected_ids):
        raise ComponentLockedRenderingError("cannot assemble incomplete component output")
    component_texts = tuple((component_id, rendered[component_id]) for component_id in expected_ids)
    combined = " ".join(text.strip() for _, text in component_texts)
    resolved_id = explanation_id or _stable_id(
        "verified-explanation", contract.contract_id, parsed.parse_id, component_texts
    )
    return VerifiedExplanation(
        explanation_id=resolved_id,
        contract_id=contract.contract_id,
        component_texts=component_texts,
        combined_text=combined,
    )
