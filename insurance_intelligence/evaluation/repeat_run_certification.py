"""Aggregate governed MO-022G live runs into non-certifying repeat-run evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping, Sequence


class RepeatRunCertificationError(ValueError):
    """Raised when repeat-run evidence violates governance invariants."""


def _stable_hash(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RepeatRunCertificationError(f"{field} must be non-empty text")
    return value.strip()


def _text_list(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RepeatRunCertificationError(f"{field} must be a text array")
    return tuple(sorted(value))


@dataclass(frozen=True)
class RepeatRunObservation:
    run_index: int
    artifact_sha256: str
    routing_decision: str
    routing_reason_codes: tuple[str, ...]
    hard_failure_codes: tuple[str, ...]
    unresolved_component_ids: tuple[str, ...]
    matched_component_ids: tuple[str, ...]
    minimum_confidence: float
    minimum_extractor_agreement: float


@dataclass(frozen=True)
class RepeatRunCertificationEvidence:
    batch_id: str
    schema_version: str
    contract_id: str
    renderer_model: str
    renderer_prompt_version: str
    extractor_model: str
    extractor_prompt_version: str
    required_run_count: int
    completed_run_count: int
    semantically_consistent: bool
    all_components_matched: bool
    hard_failure_free: bool
    unresolved_free: bool
    minimum_observed_confidence: float
    minimum_observed_extractor_agreement: float
    observations: tuple[RepeatRunObservation, ...]
    certification_effect: str
    certification_granted: bool
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_repeat_run_evidence(
    artifacts: Sequence[Mapping[str, object]], *, required_run_count: int
) -> RepeatRunCertificationEvidence:
    if isinstance(required_run_count, bool) or not isinstance(required_run_count, int) or required_run_count < 2:
        raise RepeatRunCertificationError("required_run_count must be an integer of at least 2")
    if not isinstance(artifacts, Sequence) or isinstance(artifacts, (str, bytes)):
        raise RepeatRunCertificationError("artifacts must be a sequence")
    if len(artifacts) != required_run_count:
        raise RepeatRunCertificationError("artifact count must equal required_run_count")

    observations: list[RepeatRunObservation] = []
    identity: tuple[str, str, str, str, str] | None = None
    component_signatures: list[tuple[str, ...]] = []

    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, Mapping):
            raise RepeatRunCertificationError("each artifact must be an object")
        if artifact.get("run_type") != "MO-022G_CONTROLLED_LIVE_CERTIFICATION":
            raise RepeatRunCertificationError("unsupported run_type")
        if artifact.get("certification_effect") != "NONE":
            raise RepeatRunCertificationError("live runs must have no certification effect")
        renderer = artifact.get("renderer_trace")
        extractor = artifact.get("extractor_trace")
        routing = artifact.get("routing_result")
        report = artifact.get("semantic_report")
        if not all(isinstance(item, Mapping) for item in (renderer, extractor, routing, report)):
            raise RepeatRunCertificationError("artifact traces, routing, and report must be objects")
        assert isinstance(renderer, Mapping) and isinstance(extractor, Mapping)
        assert isinstance(routing, Mapping) and isinstance(report, Mapping)

        current_identity = (
            _text(report.get("contract_id"), "contract_id"),
            _text(renderer.get("model"), "renderer.model"),
            _text(renderer.get("prompt_version"), "renderer.prompt_version"),
            _text(extractor.get("model"), "extractor.model"),
            _text(extractor.get("prompt_version"), "extractor.prompt_version"),
        )
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise RepeatRunCertificationError("all runs must use the same contract, models, and prompts")

        comparisons = report.get("comparisons")
        if not isinstance(comparisons, list) or not comparisons:
            raise RepeatRunCertificationError("semantic comparisons must not be empty")
        matched: list[str] = []
        confidences: list[float] = []
        agreements: list[float] = []
        for comparison in comparisons:
            if not isinstance(comparison, Mapping):
                raise RepeatRunCertificationError("comparison must be an object")
            confidence = comparison.get("confidence")
            agreement = comparison.get("extractor_agreement")
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise RepeatRunCertificationError("confidence must be numeric")
            if isinstance(agreement, bool) or not isinstance(agreement, (int, float)):
                raise RepeatRunCertificationError("extractor agreement must be numeric")
            confidences.append(float(confidence))
            agreements.append(float(agreement))
            if comparison.get("status") == "MATCHED":
                matched.append(_text(comparison.get("component_id"), "component_id"))
        signature = tuple(sorted(matched))
        component_signatures.append(signature)
        observations.append(
            RepeatRunObservation(
                run_index=index,
                artifact_sha256=_stable_hash(artifact),
                routing_decision=_text(routing.get("decision"), "routing.decision"),
                routing_reason_codes=_text_list(routing.get("reason_codes"), "routing.reason_codes"),
                hard_failure_codes=_text_list(report.get("hard_failure_codes"), "hard_failure_codes"),
                unresolved_component_ids=_text_list(report.get("unresolved_component_ids"), "unresolved_component_ids"),
                matched_component_ids=signature,
                minimum_confidence=min(confidences),
                minimum_extractor_agreement=min(agreements),
            )
        )

    assert identity is not None
    semantically_consistent = len(set(component_signatures)) == 1
    expected_component_count = len(component_signatures[0])
    all_components_matched = expected_component_count > 0 and all(
        len(item) == expected_component_count for item in component_signatures
    )
    hard_failure_free = all(not item.hard_failure_codes for item in observations)
    unresolved_free = all(not item.unresolved_component_ids for item in observations)
    status = (
        "READY_FOR_CERTIFICATION_DECISION"
        if semantically_consistent and all_components_matched and hard_failure_free and unresolved_free
        else "INSUFFICIENT_REPEAT_RUN_EVIDENCE"
    )
    signature = {
        "identity": identity,
        "required_run_count": required_run_count,
        "observations": [asdict(item) for item in observations],
    }
    return RepeatRunCertificationEvidence(
        batch_id=f"repeat-run-evidence-{_stable_hash(signature)[:16]}",
        schema_version="1.0",
        contract_id=identity[0],
        renderer_model=identity[1],
        renderer_prompt_version=identity[2],
        extractor_model=identity[3],
        extractor_prompt_version=identity[4],
        required_run_count=required_run_count,
        completed_run_count=len(observations),
        semantically_consistent=semantically_consistent,
        all_components_matched=all_components_matched,
        hard_failure_free=hard_failure_free,
        unresolved_free=unresolved_free,
        minimum_observed_confidence=min(item.minimum_confidence for item in observations),
        minimum_observed_extractor_agreement=min(item.minimum_extractor_agreement for item in observations),
        observations=tuple(observations),
        certification_effect="NONE",
        certification_granted=False,
        status=status,
    )


__all__ = [
    "RepeatRunCertificationError",
    "RepeatRunCertificationEvidence",
    "RepeatRunObservation",
    "build_repeat_run_evidence",
]
