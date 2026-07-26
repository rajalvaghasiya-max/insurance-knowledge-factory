"""Real governed knowledge-to-explanation certification cycle for MO-023H.

The cycle composes the existing Star Comprehensive knowledge-build pilot and
certified-product response pilot. It does not recrawl, reinterpret, or bypass
any governed artifact. The certified snapshot emitted by the build is passed
unchanged into the response cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping

from insurance_intelligence.orchestration.star_comprehensive_knowledge_build import (
    StarKnowledgeBuildError,
    StarKnowledgeBuildResult,
    build_star_comprehensive_copay_snapshot,
)
from insurance_intelligence.orchestration.star_comprehensive_pilot import (
    PRODUCT_REFERENCE,
    TOPIC,
    StarComprehensivePilotError,
    StarComprehensivePilotResult,
    run_star_comprehensive_copay_pilot,
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
    response: StarComprehensivePilotResult
    released_response_id: str
    limitations: tuple[str, ...]
    status: str


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
) -> FullKnowledgeToExplanationResult:
    """Certify governed knowledge and use that exact snapshot to generate a response."""
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
        response = run_star_comprehensive_copay_pilot(
            request_id=response_request_id,
            question=question,
            repository_root=response_root,
            knowledge_snapshot_id=build.knowledge_snapshot_id,
            customer_context=customer_context,
            audience=audience,
            reading_level=reading_level,
        )
    except StarComprehensivePilotError as exc:
        raise FullCycleCertificationError(f"response certification failed: {exc}") from exc

    if response.product_reference != build.product_reference or response.topic != build.topic:
        raise FullCycleCertificationError("response scope diverged from certified knowledge scope")
    if response.knowledge_snapshot_id != build.knowledge_snapshot_id:
        raise FullCycleCertificationError("response did not consume the certified snapshot")
    if response.released_response_id != response.response.response_id:
        raise FullCycleCertificationError("released response identity is inconsistent")

    limitations = tuple(dict.fromkeys(build.limitations + response.limitations))
    certification_id = _stable_id(
        "full-cycle-certification",
        build.build_id,
        build.knowledge_snapshot_id,
        response.pilot_id,
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
