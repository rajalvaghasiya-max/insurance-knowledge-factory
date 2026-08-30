"""Real governed knowledge-to-explanation certification cycle for MO-023H.

The cycle composes the existing Star Comprehensive knowledge-build pilot and
the current guarded response pilot. It does not recrawl, reinterpret, or bypass
any governed artifact. The certified snapshot emitted by the build is passed
unchanged into the response cycle, and CERTIFIED now requires evidence that the
post-C5.36 safety boundaries were actually exercised.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping

from insurance_intelligence.orchestration.guarded_star_comprehensive_pilot import (
    GuardedStarComprehensivePilotError,
    GuardedStarComprehensivePilotResult,
    PRODUCT_REFERENCE,
    TOPIC,
    run_guarded_star_comprehensive_copay_pilot,
)
from insurance_intelligence.orchestration.star_comprehensive_knowledge_build import (
    StarKnowledgeBuildError,
    StarKnowledgeBuildResult,
    build_star_comprehensive_copay_snapshot,
)


class FullCycleCertificationError(ValueError):
    """Raised when the governed full certification cycle cannot complete safely."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class FullKnowledgeToExplanationResult:
    certification_id: str
    build_request_id: str
    response_request_id: str
    product_reference: str
    topic: str
    question: str
    knowledge_snapshot_id: str
    build: StarKnowledgeBuildResult
    response: GuardedStarComprehensivePilotResult
    released_response_id: str
    limitations: tuple[str, ...]
    status: str


def _validate_guarded_response(response: GuardedStarComprehensivePilotResult) -> None:
    if not isinstance(response, GuardedStarComprehensivePilotResult):
        raise FullCycleCertificationError("response is not a guarded Star pilot result")
    if response.guard_status != "GUARDED":
        raise FullCycleCertificationError("guarded response status is missing")
    if response.instance_sufficiency.outcome != "PASS" or not response.instance_sufficiency.planning_authorized:
        raise FullCycleCertificationError("guarded response did not pass Instance Sufficiency")
    if (
        response.evidence_enforcement.outcome != "EVIDENCE_RESOLUTION_AUTHORIZED"
        or not response.evidence_enforcement.evidence_resolver_called
        or response.evidence_enforcement.evidence_output is None
    ):
        raise FullCycleCertificationError("guarded response did not exercise Evidence Instance Enforcement")
    if (
        response.authority_enforcement.enforcement_outcome != "DELEGATED_TO_DECISION_GATE"
        or not response.authority_enforcement.decision_gate_called
        or response.authority_enforcement.decision_output is None
    ):
        raise FullCycleCertificationError("guarded response did not exercise Authority-Enforced Decision")
    if response.render_conformance.outcome != "PASS" or response.render_conformance.rendered_text is None:
        raise FullCycleCertificationError("guarded response did not pass Rendering Exit Safety")
    if response.identity_resolution.status != "RESOLVED" or not response.identity_record_hash:
        raise FullCycleCertificationError("guarded response did not preserve governed product identity")


def run_full_knowledge_to_explanation_certification(
    *,
    repository_root: str | Path,
    build_request_id: str,
    response_request_id: str,
    question: str,
    customer_context: Mapping[str, object] | None = None,
    audience: str = "CUSTOMER",
    reading_level: str = "SIMPLE",
    artifact_paths: Mapping[str, str] | None = None,
    response_repository_root: str | Path | None = None,
    identity_reference_path: str | Path | None = None,
    document_identity_overlay_path: str | Path | None = None,
) -> FullKnowledgeToExplanationResult:
    """Certify governed knowledge and use that exact snapshot on the guarded response path."""
    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise FullCycleCertificationError("repository_root must be an existing directory")
    if not isinstance(response_request_id, str) or not response_request_id.strip():
        raise FullCycleCertificationError("response_request_id must be a non-empty string")
    if not isinstance(question, str) or not question.strip():
        raise FullCycleCertificationError("question must be a non-empty string")

    try:
        build = build_star_comprehensive_copay_snapshot(
            repository_root=root,
            build_request_id=build_request_id,
            artifact_paths=artifact_paths,
        )
    except StarKnowledgeBuildError as exc:
        raise FullCycleCertificationError(f"knowledge certification failed: {exc}") from exc

    if build.status != "CERTIFIED":
        raise FullCycleCertificationError("knowledge build did not produce a certified snapshot")
    if build.product_reference != PRODUCT_REFERENCE or build.topic != TOPIC:
        raise FullCycleCertificationError("certified knowledge scope does not match response pilot")
    if not build.knowledge_snapshot_id:
        raise FullCycleCertificationError("certified knowledge snapshot identity is missing")

    response_root = (
        Path(response_repository_root).resolve()
        if response_repository_root is not None
        else (root / "knowledge" / "factory" / "registry_backed").resolve()
    )
    try:
        response = run_guarded_star_comprehensive_copay_pilot(
            request_id=response_request_id,
            question=question,
            repository_root=response_root,
            knowledge_snapshot_id=build.knowledge_snapshot_id,
            customer_context=customer_context,
            audience=audience,
            reading_level=reading_level,
            identity_reference_path=identity_reference_path,
            document_identity_overlay_path=document_identity_overlay_path,
        )
    except GuardedStarComprehensivePilotError as exc:
        raise FullCycleCertificationError(f"response certification failed: {exc}") from exc

    _validate_guarded_response(response)
    if response.product_reference != build.product_reference or response.topic != build.topic:
        raise FullCycleCertificationError("response scope diverged from certified knowledge scope")
    if response.knowledge_snapshot_id != build.knowledge_snapshot_id:
        raise FullCycleCertificationError("response did not consume the certified snapshot")
    if response.released_response_id != response.response.response_id:
        raise FullCycleCertificationError("released response identity is inconsistent")

    limitations = tuple(dict.fromkeys(build.limitations + response.limitations))
    certification_id = _stable_id(
        "guarded-full-cycle-certification",
        build.build_id,
        build.knowledge_snapshot_id,
        response.pilot_id,
        response.identity_record_hash,
        response.temporal_status,
        response.released_response_id,
    )
    return FullKnowledgeToExplanationResult(
        certification_id=certification_id,
        build_request_id=build_request_id.strip(),
        response_request_id=response_request_id.strip(),
        product_reference=build.product_reference,
        topic=build.topic,
        question=question.strip(),
        knowledge_snapshot_id=build.knowledge_snapshot_id,
        build=build,
        response=response,
        released_response_id=response.released_response_id,
        limitations=limitations,
        status="CERTIFIED",
    )
