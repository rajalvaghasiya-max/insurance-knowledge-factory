"""Aggregate governed OpenAI+Gemini runs into non-certifying stability evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence


class CrossProviderRepeatRunError(ValueError):
    """Raised when cross-provider batch evidence violates invariants."""


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CrossProviderRepeatRunError(f"{field} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class CrossProviderRunObservation:
    run_index: int
    artifact_sha256: str
    routing_decision: str
    routing_reason_codes: tuple[str, ...]
    agreed_component_ids: tuple[str, ...]
    matched_component_ids: tuple[str, ...]
    hard_failure_codes: tuple[str, ...]
    unresolved_component_ids: tuple[str, ...]
    minimum_confidence: float
    renderer_latency_ms: int
    openai_extractor_latency_ms: int
    gemini_extractor_latency_ms: int


@dataclass(frozen=True)
class CrossProviderRepeatRunEvidence:
    batch_id: str
    schema_version: str
    contract_id: str
    rule_family_id: str
    rule_family_version: str
    renderer_model: str
    renderer_prompt_version: str
    openai_extractor_model: str
    openai_extractor_prompt_version: str
    gemini_extractor_model: str
    gemini_extractor_prompt_version: str
    data_classification: str
    required_run_count: int
    completed_run_count: int
    exact_agreement_every_run: bool
    all_components_matched: bool
    hard_failure_free: bool
    unresolved_free: bool
    preflight_passed_every_run: bool
    minimum_observed_confidence: float
    observations: tuple[CrossProviderRunObservation, ...]
    certification_effect: str
    certification_granted: bool
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_cross_provider_repeat_run_evidence(
    artifacts: Sequence[Mapping[str, object]], *, required_run_count: int
) -> CrossProviderRepeatRunEvidence:
    if isinstance(required_run_count, bool) or not isinstance(required_run_count, int) or required_run_count < 2:
        raise CrossProviderRepeatRunError("required_run_count must be at least 2")
    if len(artifacts) != required_run_count:
        raise CrossProviderRepeatRunError("artifact count must equal required_run_count")

    identity: tuple[str, ...] | None = None
    expected_components: tuple[str, ...] | None = None
    observations: list[CrossProviderRunObservation] = []
    preflights: list[bool] = []

    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, Mapping):
            raise CrossProviderRepeatRunError("each artifact must be an object")
        if artifact.get("run_type") != "MO-022G_OPENAI_GEMINI_CROSS_PROVIDER":
            raise CrossProviderRepeatRunError("unsupported run_type")
        if artifact.get("certification_effect") != "NONE" or artifact.get("certification_granted") is not False:
            raise CrossProviderRepeatRunError("artifacts must have no certification effect")

        renderer = artifact.get("renderer_trace")
        openai = artifact.get("openai_extractor_trace")
        gemini = artifact.get("gemini_extractor_trace")
        routing = artifact.get("routing_result")
        report = artifact.get("semantic_report")
        agreements = artifact.get("agreements")
        preflight = artifact.get("rule_family_preflight")
        if not all(isinstance(item, Mapping) for item in (renderer, openai, gemini, routing, report, preflight)):
            raise CrossProviderRepeatRunError("traces, routing, report, and preflight must be objects")
        if not isinstance(agreements, list) or not agreements:
            raise CrossProviderRepeatRunError("agreements must not be empty")
        assert isinstance(renderer, Mapping) and isinstance(openai, Mapping)
        assert isinstance(gemini, Mapping) and isinstance(routing, Mapping)
        assert isinstance(report, Mapping) and isinstance(preflight, Mapping)

        current_identity = (
            _text(report.get("contract_id"), "contract_id"),
            _text(preflight.get("family_id"), "preflight.family_id"),
            _text(preflight.get("family_version"), "preflight.family_version"),
            _text(renderer.get("model"), "renderer.model"),
            _text(renderer.get("prompt_version"), "renderer.prompt_version"),
            _text(openai.get("model"), "openai.model"),
            _text(openai.get("prompt_version"), "openai.prompt_version"),
            _text(gemini.get("model"), "gemini.model"),
            _text(gemini.get("prompt_version"), "gemini.prompt_version"),
            _text(artifact.get("data_classification"), "data_classification"),
        )
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise CrossProviderRepeatRunError("all runs must use an identical governed tuple")

        all_ids = tuple(sorted(
            _text(item.get("component_id"), "agreement.component_id")
            for item in agreements if isinstance(item, Mapping)
        ))
        agreed_ids = tuple(sorted(
            _text(item.get("component_id"), "agreement.component_id")
            for item in agreements if isinstance(item, Mapping) and item.get("agreed") is True
        ))
        if expected_components is None:
            expected_components = all_ids
        elif all_ids != expected_components:
            raise CrossProviderRepeatRunError("component identities must remain stable across runs")

        comparisons = report.get("comparisons")
        if not isinstance(comparisons, list) or not comparisons:
            raise CrossProviderRepeatRunError("semantic comparisons must not be empty")
        matched_ids: list[str] = []
        confidences: list[float] = []
        for item in comparisons:
            if not isinstance(item, Mapping):
                raise CrossProviderRepeatRunError("comparison must be an object")
            confidence = item.get("confidence")
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise CrossProviderRepeatRunError("confidence must be numeric")
            confidences.append(float(confidence))
            if item.get("status") == "MATCHED":
                matched_ids.append(_text(item.get("component_id"), "comparison.component_id"))

        reason_codes = routing.get("reason_codes")
        hard_failures = report.get("hard_failure_codes")
        unresolved = report.get("unresolved_component_ids")
        if not all(isinstance(value, list) and all(isinstance(x, str) for x in value)
                   for value in (reason_codes, hard_failures, unresolved)):
            raise CrossProviderRepeatRunError("reason and failure fields must be text arrays")

        latency_values = (
            renderer.get("latency_ms"), openai.get("latency_ms"), gemini.get("latency_ms")
        )
        if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in latency_values):
            raise CrossProviderRepeatRunError("latencies must be non-negative integers")

        preflight_passed = preflight.get("status") == "PASSED"
        preflights.append(preflight_passed)
        observations.append(CrossProviderRunObservation(
            run_index=index,
            artifact_sha256=_hash(artifact),
            routing_decision=_text(routing.get("decision"), "routing.decision"),
            routing_reason_codes=tuple(sorted(reason_codes)),
            agreed_component_ids=agreed_ids,
            matched_component_ids=tuple(sorted(matched_ids)),
            hard_failure_codes=tuple(sorted(hard_failures)),
            unresolved_component_ids=tuple(sorted(unresolved)),
            minimum_confidence=min(confidences),
            renderer_latency_ms=int(latency_values[0]),
            openai_extractor_latency_ms=int(latency_values[1]),
            gemini_extractor_latency_ms=int(latency_values[2]),
        ))

    assert identity is not None and expected_components is not None
    exact_agreement = all(item.agreed_component_ids == expected_components for item in observations)
    all_matched = all(item.matched_component_ids == expected_components for item in observations)
    hard_failure_free = all(not item.hard_failure_codes for item in observations)
    unresolved_free = all(not item.unresolved_component_ids for item in observations)
    preflight_passed = all(preflights)
    stable = exact_agreement and all_matched and hard_failure_free and unresolved_free and preflight_passed
    status = "CROSS_PROVIDER_SEMANTICALLY_STABLE" if stable else "INSUFFICIENT_CROSS_PROVIDER_STABILITY"
    signature = {"identity": identity, "observations": [asdict(item) for item in observations]}
    return CrossProviderRepeatRunEvidence(
        batch_id=f"cross-provider-repeat-evidence-{_hash(signature)[:16]}",
        schema_version="1.0",
        contract_id=identity[0],
        rule_family_id=identity[1],
        rule_family_version=identity[2],
        renderer_model=identity[3],
        renderer_prompt_version=identity[4],
        openai_extractor_model=identity[5],
        openai_extractor_prompt_version=identity[6],
        gemini_extractor_model=identity[7],
        gemini_extractor_prompt_version=identity[8],
        data_classification=identity[9],
        required_run_count=required_run_count,
        completed_run_count=len(observations),
        exact_agreement_every_run=exact_agreement,
        all_components_matched=all_matched,
        hard_failure_free=hard_failure_free,
        unresolved_free=unresolved_free,
        preflight_passed_every_run=preflight_passed,
        minimum_observed_confidence=min(item.minimum_confidence for item in observations),
        observations=tuple(observations),
        certification_effect="NONE",
        certification_granted=False,
        status=status,
    )


__all__ = [
    "CrossProviderRepeatRunError",
    "CrossProviderRepeatRunEvidence",
    "CrossProviderRunObservation",
    "build_cross_provider_repeat_run_evidence",
]
