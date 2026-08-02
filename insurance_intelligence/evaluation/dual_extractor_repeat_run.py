"""Aggregate governed dual-extractor live runs into non-certifying evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence


class DualExtractorRepeatRunError(ValueError):
    """Raised when dual-extractor batch evidence violates invariants."""


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DualExtractorRepeatRunError(f"{field} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class DualExtractorRunObservation:
    run_index: int
    artifact_sha256: str
    routing_decision: str
    routing_reason_codes: tuple[str, ...]
    agreed_component_ids: tuple[str, ...]
    matched_component_ids: tuple[str, ...]
    hard_failure_codes: tuple[str, ...]
    unresolved_component_ids: tuple[str, ...]
    minimum_confidence: float


@dataclass(frozen=True)
class DualExtractorRepeatRunEvidence:
    batch_id: str
    schema_version: str
    contract_id: str
    renderer_model: str
    renderer_prompt_version: str
    extractor_a_model: str
    extractor_a_prompt_version: str
    extractor_b_model: str
    extractor_b_prompt_version: str
    required_run_count: int
    completed_run_count: int
    exact_agreement_every_run: bool
    all_components_matched: bool
    hard_failure_free: bool
    unresolved_free: bool
    minimum_observed_confidence: float
    observations: tuple[DualExtractorRunObservation, ...]
    certification_effect: str
    certification_granted: bool
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_dual_extractor_repeat_run_evidence(
    artifacts: Sequence[Mapping[str, object]], *, required_run_count: int
) -> DualExtractorRepeatRunEvidence:
    if isinstance(required_run_count, bool) or not isinstance(required_run_count, int) or required_run_count < 2:
        raise DualExtractorRepeatRunError("required_run_count must be at least 2")
    if len(artifacts) != required_run_count:
        raise DualExtractorRepeatRunError("artifact count must equal required_run_count")

    identity: tuple[str, ...] | None = None
    observations: list[DualExtractorRunObservation] = []
    expected_components: tuple[str, ...] | None = None

    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, Mapping):
            raise DualExtractorRepeatRunError("each artifact must be an object")
        if artifact.get("run_type") != "MO-022G_DUAL_EXTRACTOR_LIVE_CERTIFICATION":
            raise DualExtractorRepeatRunError("unsupported run_type")
        if artifact.get("certification_effect") != "NONE" or artifact.get("certification_granted") is not False:
            raise DualExtractorRepeatRunError("artifacts must have no certification effect")

        renderer = artifact.get("renderer_trace")
        extractor_a = artifact.get("extractor_a_trace")
        extractor_b = artifact.get("extractor_b_trace")
        routing = artifact.get("routing_result")
        report = artifact.get("semantic_report")
        agreements = artifact.get("agreements")
        if not all(isinstance(item, Mapping) for item in (renderer, extractor_a, extractor_b, routing, report)):
            raise DualExtractorRepeatRunError("traces, routing, and report must be objects")
        if not isinstance(agreements, list) or not agreements:
            raise DualExtractorRepeatRunError("agreements must not be empty")
        assert isinstance(renderer, Mapping) and isinstance(extractor_a, Mapping)
        assert isinstance(extractor_b, Mapping) and isinstance(routing, Mapping)
        assert isinstance(report, Mapping)

        current_identity = (
            _text(report.get("contract_id"), "contract_id"),
            _text(renderer.get("model"), "renderer.model"),
            _text(renderer.get("prompt_version"), "renderer.prompt_version"),
            _text(extractor_a.get("model"), "extractor_a.model"),
            _text(extractor_a.get("prompt_version"), "extractor_a.prompt_version"),
            _text(extractor_b.get("model"), "extractor_b.model"),
            _text(extractor_b.get("prompt_version"), "extractor_b.prompt_version"),
        )
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise DualExtractorRepeatRunError("all runs must use identical contract, models, and prompts")

        agreed_ids = tuple(sorted(
            _text(item.get("component_id"), "agreement.component_id")
            for item in agreements
            if isinstance(item, Mapping) and item.get("agreed") is True
        ))
        all_agreement_ids = tuple(sorted(
            _text(item.get("component_id"), "agreement.component_id")
            for item in agreements if isinstance(item, Mapping)
        ))
        if expected_components is None:
            expected_components = all_agreement_ids
        elif all_agreement_ids != expected_components:
            raise DualExtractorRepeatRunError("component identities must remain stable across runs")

        comparisons = report.get("comparisons")
        if not isinstance(comparisons, list) or not comparisons:
            raise DualExtractorRepeatRunError("semantic comparisons must not be empty")
        matched_ids: list[str] = []
        confidences: list[float] = []
        for item in comparisons:
            if not isinstance(item, Mapping):
                raise DualExtractorRepeatRunError("comparison must be an object")
            confidence = item.get("confidence")
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise DualExtractorRepeatRunError("confidence must be numeric")
            confidences.append(float(confidence))
            if item.get("status") == "MATCHED":
                matched_ids.append(_text(item.get("component_id"), "comparison.component_id"))

        reason_codes = routing.get("reason_codes")
        hard_failures = report.get("hard_failure_codes")
        unresolved = report.get("unresolved_component_ids")
        if not all(isinstance(value, list) and all(isinstance(x, str) for x in value)
                   for value in (reason_codes, hard_failures, unresolved)):
            raise DualExtractorRepeatRunError("reason and failure fields must be text arrays")

        observations.append(DualExtractorRunObservation(
            run_index=index,
            artifact_sha256=_hash(artifact),
            routing_decision=_text(routing.get("decision"), "routing.decision"),
            routing_reason_codes=tuple(sorted(reason_codes)),
            agreed_component_ids=agreed_ids,
            matched_component_ids=tuple(sorted(matched_ids)),
            hard_failure_codes=tuple(sorted(hard_failures)),
            unresolved_component_ids=tuple(sorted(unresolved)),
            minimum_confidence=min(confidences),
        ))

    assert identity is not None and expected_components is not None
    exact_agreement = all(item.agreed_component_ids == expected_components for item in observations)
    all_matched = all(item.matched_component_ids == expected_components for item in observations)
    hard_failure_free = all(not item.hard_failure_codes for item in observations)
    unresolved_free = all(not item.unresolved_component_ids for item in observations)
    status = (
        "READY_FOR_CERTIFICATION_DECISION"
        if exact_agreement and all_matched and hard_failure_free and unresolved_free
        else "INSUFFICIENT_DUAL_EXTRACTOR_EVIDENCE"
    )
    signature = {"identity": identity, "observations": [asdict(item) for item in observations]}
    return DualExtractorRepeatRunEvidence(
        batch_id=f"dual-extractor-repeat-evidence-{_hash(signature)[:16]}",
        schema_version="1.0",
        contract_id=identity[0],
        renderer_model=identity[1],
        renderer_prompt_version=identity[2],
        extractor_a_model=identity[3],
        extractor_a_prompt_version=identity[4],
        extractor_b_model=identity[5],
        extractor_b_prompt_version=identity[6],
        required_run_count=required_run_count,
        completed_run_count=len(observations),
        exact_agreement_every_run=exact_agreement,
        all_components_matched=all_matched,
        hard_failure_free=hard_failure_free,
        unresolved_free=unresolved_free,
        minimum_observed_confidence=min(item.minimum_confidence for item in observations),
        observations=tuple(observations),
        certification_effect="NONE",
        certification_granted=False,
        status=status,
    )


__all__ = [
    "DualExtractorRepeatRunError",
    "DualExtractorRepeatRunEvidence",
    "DualExtractorRunObservation",
    "build_dual_extractor_repeat_run_evidence",
]
