"""Strict parser for structured controlled-LLM rendering output (MO-022D)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence

from insurance_intelligence.contracts.llm_rendering import (
    CandidateRenderedSection,
    ProviderRenderRequest,
    build_candidate_section,
)


class LLMOutputParseError(ValueError):
    """Raised when provider output is malformed or exceeds the requested scope."""


@dataclass(frozen=True)
class ParsedProviderOutput:
    parse_id: str
    provider_request_id: str
    candidate_sections: tuple[CandidateRenderedSection, ...]
    canonical_payload: str


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _tuple_of_strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LLMOutputParseError(f"{label} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LLMOutputParseError(f"{label} values must be non-empty strings")
        result.append(item)
    if len(result) != len(set(result)):
        raise LLMOutputParseError(f"{label} values must be unique")
    return tuple(result)


def _load_payload(raw_output: str | Mapping[str, object]) -> dict[str, object]:
    if isinstance(raw_output, str):
        try:
            loaded = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise LLMOutputParseError("provider output is not valid JSON") from exc
    elif isinstance(raw_output, Mapping):
        loaded = dict(raw_output)
    else:
        raise LLMOutputParseError("provider output must be JSON text or a mapping")
    if not isinstance(loaded, dict):
        raise LLMOutputParseError("provider output root must be an object")
    if set(loaded) != {"sections"}:
        raise LLMOutputParseError("provider output must contain only the sections field")
    return loaded


def parse_provider_output(
    raw_output: str | Mapping[str, object],
    request: ProviderRenderRequest,
) -> ParsedProviderOutput:
    """Parse provider JSON and enforce exact section identity and scope."""
    if not isinstance(request, ProviderRenderRequest):
        raise TypeError("request must be ProviderRenderRequest")
    payload = _load_payload(raw_output)
    raw_sections = payload["sections"]
    if not isinstance(raw_sections, list) or not raw_sections:
        raise LLMOutputParseError("sections must be a non-empty list")

    required_keys = {
        "section_id", "source_section_id", "section_type", "text",
        "approved_finding_ids", "evidence_ids", "limitation_ids", "clarification_ids",
    }
    parsed: list[CandidateRenderedSection] = []
    for index, item in enumerate(raw_sections):
        if not isinstance(item, dict):
            raise LLMOutputParseError(f"sections[{index}] must be an object")
        if set(item) != required_keys:
            missing = sorted(required_keys - set(item))
            extra = sorted(set(item) - required_keys)
            raise LLMOutputParseError(f"sections[{index}] has invalid fields; missing={missing}, extra={extra}")
        for key in ("section_id", "source_section_id", "section_type", "text"):
            if not isinstance(item[key], str) or not item[key].strip():
                raise LLMOutputParseError(f"sections[{index}].{key} must be a non-empty string")
        parsed.append(build_candidate_section(
            section_id=item["section_id"],
            source_section_id=item["source_section_id"],
            section_type=item["section_type"],
            text=item["text"],
            approved_finding_ids=_tuple_of_strings(item["approved_finding_ids"], f"sections[{index}].approved_finding_ids"),
            evidence_ids=_tuple_of_strings(item["evidence_ids"], f"sections[{index}].evidence_ids"),
            limitation_ids=_tuple_of_strings(item["limitation_ids"], f"sections[{index}].limitation_ids"),
            clarification_ids=_tuple_of_strings(item["clarification_ids"], f"sections[{index}].clarification_ids"),
        ))

    source_ids = tuple(section.source_section_id for section in parsed)
    if len(source_ids) != len(set(source_ids)):
        raise LLMOutputParseError("candidate source_section_id values must be unique")
    if set(source_ids) != set(request.packet.source_section_ids):
        raise LLMOutputParseError("candidate sections must exactly cover requested source sections")
    if any(not set(s.approved_finding_ids) <= set(request.packet.approved_finding_ids) for s in parsed):
        raise LLMOutputParseError("candidate exposes finding outside approved scope")
    if any(not set(s.evidence_ids) <= set(request.packet.approved_evidence_ids) for s in parsed):
        raise LLMOutputParseError("candidate exposes evidence outside approved scope")
    if any(not set(s.limitation_ids) <= set(request.packet.limitation_ids) for s in parsed):
        raise LLMOutputParseError("candidate exposes limitation outside approved scope")
    if any(not set(s.clarification_ids) <= set(request.packet.clarification_ids) for s in parsed):
        raise LLMOutputParseError("candidate exposes clarification outside approved scope")

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return ParsedProviderOutput(
        parse_id=_stable_id("llm-parse", request.provider_request_id, canonical),
        provider_request_id=request.provider_request_id,
        candidate_sections=tuple(sorted(parsed, key=lambda s: request.packet.source_section_ids.index(s.source_section_id))),
        canonical_payload=canonical,
    )
