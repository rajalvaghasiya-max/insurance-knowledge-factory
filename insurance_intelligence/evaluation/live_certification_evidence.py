"""Governed evidence projection for MO-022G controlled live runs.

Raw provider prompts and outputs remain local. This module produces a compact,
reviewable projection containing only hashes, semantic outcomes, routing facts,
and the explicit non-certification state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Mapping


class LiveCertificationEvidenceError(ValueError):
    """Raised when a live-run artifact cannot become governed evidence."""


def _stable_hash(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _required_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LiveCertificationEvidenceError(f"{field_name} must be an object")
    return value


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiveCertificationEvidenceError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class LiveComponentEvidence:
    component_id: str
    status: str
    confidence: float
    extractor_agreement: float
    mismatch_codes: tuple[str, ...]


@dataclass(frozen=True)
class GovernedLiveCertificationEvidence:
    evidence_id: str
    schema_version: str
    source_run_type: str
    source_artifact_sha256: str
    contract_id: str
    renderer_model: str
    renderer_prompt_version: str
    extractor_model: str
    extractor_prompt_version: str
    routing_decision: str
    routing_reason_codes: tuple[str, ...]
    hard_failure_codes: tuple[str, ...]
    unresolved_component_ids: tuple[str, ...]
    components: tuple[LiveComponentEvidence, ...]
    certification_effect: str
    certification_granted: bool
    reviewer_decision: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_governed_live_evidence(
    artifact: Mapping[str, object],
) -> GovernedLiveCertificationEvidence:
    if not isinstance(artifact, Mapping):
        raise LiveCertificationEvidenceError("artifact must be an object")

    run_type = _required_text(artifact.get("run_type"), "run_type")
    if run_type != "MO-022G_CONTROLLED_LIVE_CERTIFICATION":
        raise LiveCertificationEvidenceError("unsupported run_type")
    certification_effect = _required_text(
        artifact.get("certification_effect"), "certification_effect"
    )
    if certification_effect != "NONE":
        raise LiveCertificationEvidenceError(
            "controlled evidence projection cannot grant certification"
        )

    renderer = _required_mapping(artifact.get("renderer_trace"), "renderer_trace")
    extractor = _required_mapping(artifact.get("extractor_trace"), "extractor_trace")
    routing = _required_mapping(artifact.get("routing_result"), "routing_result")
    report = _required_mapping(artifact.get("semantic_report"), "semantic_report")

    comparisons = report.get("comparisons")
    if not isinstance(comparisons, list) or not comparisons:
        raise LiveCertificationEvidenceError("semantic_report.comparisons must not be empty")

    components: list[LiveComponentEvidence] = []
    for item in comparisons:
        comparison = _required_mapping(item, "comparison")
        confidence = comparison.get("confidence")
        agreement = comparison.get("extractor_agreement")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise LiveCertificationEvidenceError("comparison confidence must be numeric")
        if isinstance(agreement, bool) or not isinstance(agreement, (int, float)):
            raise LiveCertificationEvidenceError(
                "comparison extractor_agreement must be numeric"
            )
        mismatch_codes = comparison.get("mismatch_codes")
        if not isinstance(mismatch_codes, list) or not all(
            isinstance(value, str) for value in mismatch_codes
        ):
            raise LiveCertificationEvidenceError("mismatch_codes must be text array")
        components.append(
            LiveComponentEvidence(
                component_id=_required_text(
                    comparison.get("component_id"), "comparison.component_id"
                ),
                status=_required_text(comparison.get("status"), "comparison.status"),
                confidence=float(confidence),
                extractor_agreement=float(agreement),
                mismatch_codes=tuple(sorted(mismatch_codes)),
            )
        )

    ordered_components = tuple(sorted(components, key=lambda item: item.component_id))
    if len({item.component_id for item in ordered_components}) != len(ordered_components):
        raise LiveCertificationEvidenceError("component ids must be unique")

    reason_codes = routing.get("reason_codes")
    hard_failures = report.get("hard_failure_codes")
    unresolved = report.get("unresolved_component_ids")
    for value, field_name in (
        (reason_codes, "routing_result.reason_codes"),
        (hard_failures, "semantic_report.hard_failure_codes"),
        (unresolved, "semantic_report.unresolved_component_ids"),
    ):
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise LiveCertificationEvidenceError(f"{field_name} must be a text array")

    artifact_hash = _stable_hash(artifact)
    signature = {
        "artifact_hash": artifact_hash,
        "contract_id": report.get("contract_id"),
        "decision": routing.get("decision"),
        "components": [asdict(item) for item in ordered_components],
    }
    return GovernedLiveCertificationEvidence(
        evidence_id=f"live-certification-evidence-{_stable_hash(signature)[:16]}",
        schema_version="1.0",
        source_run_type=run_type,
        source_artifact_sha256=artifact_hash,
        contract_id=_required_text(report.get("contract_id"), "semantic_report.contract_id"),
        renderer_model=_required_text(renderer.get("model"), "renderer_trace.model"),
        renderer_prompt_version=_required_text(
            renderer.get("prompt_version"), "renderer_trace.prompt_version"
        ),
        extractor_model=_required_text(extractor.get("model"), "extractor_trace.model"),
        extractor_prompt_version=_required_text(
            extractor.get("prompt_version"), "extractor_trace.prompt_version"
        ),
        routing_decision=_required_text(routing.get("decision"), "routing_result.decision"),
        routing_reason_codes=tuple(sorted(reason_codes)),
        hard_failure_codes=tuple(sorted(hard_failures)),
        unresolved_component_ids=tuple(sorted(unresolved)),
        components=ordered_components,
        certification_effect=certification_effect,
        certification_granted=False,
        reviewer_decision="PENDING",
    )


__all__ = [
    "GovernedLiveCertificationEvidence",
    "LiveCertificationEvidenceError",
    "LiveComponentEvidence",
    "build_governed_live_evidence",
]
