"""Production adapter for publication-backed USER_ANSWER evidence resolution.

This module binds the existing guarded orchestration evidence stage to the
publication-backed Evidence Resolver introduced by Issue #229.  It is intentionally
concept-neutral: callers provide an EvidenceResolverInput factory and a published
resolver, while this adapter enforces the downstream-use boundary and normalises the
result into the existing orchestration adapter contract.
"""
from __future__ import annotations

from typing import Callable

from insurance_intelligence.contracts.evidence import EvidenceResolverInput
from insurance_intelligence.contracts.full_cycle import OrchestrationRequest
from insurance_intelligence.evidence.admission import USER_ANSWER, evidence_use_from_context
from insurance_intelligence.evidence.published_resolver import PublishedEvidenceResolver
from insurance_intelligence.orchestration.intelligence_adapters import (
    IntelligenceStageAdapter,
    RawIntelligenceStageOutput,
    build_intelligence_stage_adapter,
    build_raw_intelligence_stage_output,
)

EVIDENCE_STAGE = "EVIDENCE_RESOLUTION_ENFORCED"


class UserAnswerEvidenceAdapterError(ValueError):
    """Raised when the production answer-evidence stage is configured unsafely."""


EvidenceInputFactory = Callable[[OrchestrationRequest], EvidenceResolverInput]


def build_user_answer_evidence_stage_adapter(
    *,
    resolver: PublishedEvidenceResolver,
    evidence_input_factory: EvidenceInputFactory,
) -> IntelligenceStageAdapter:
    """Build the governed evidence stage for ordinary user-answer execution.

    The factory must return an EvidenceResolverInput explicitly marked USER_ANSWER.
    INTERNAL_CERTIFICATION or implicit legacy evidence use is rejected before resolution.
    The resolver itself is publication-backed, so raw governed bindings cannot be admitted
    through this production adapter.
    """
    if not isinstance(resolver, PublishedEvidenceResolver):
        raise UserAnswerEvidenceAdapterError(
            "resolver must be a PublishedEvidenceResolver"
        )
    if not callable(evidence_input_factory):
        raise UserAnswerEvidenceAdapterError("evidence_input_factory must be callable")

    def capability(
        *,
        request: OrchestrationRequest,
        stage: str,
        input_ids: tuple[str, ...],
        knowledge_snapshot_id: str,
    ) -> RawIntelligenceStageOutput:
        if stage != EVIDENCE_STAGE:
            raise UserAnswerEvidenceAdapterError(
                f"user-answer evidence adapter may run only at {EVIDENCE_STAGE}"
            )
        evidence_input = evidence_input_factory(request)
        if not isinstance(evidence_input, EvidenceResolverInput):
            raise UserAnswerEvidenceAdapterError(
                "evidence_input_factory must return EvidenceResolverInput"
            )
        if evidence_input.request_id != request.execution_id:
            raise UserAnswerEvidenceAdapterError(
                "evidence input request_id must match orchestration execution_id"
            )
        if evidence_use_from_context(evidence_input.resolution_context) != USER_ANSWER:
            raise UserAnswerEvidenceAdapterError(
                "production response evidence must explicitly use USER_ANSWER"
            )

        output = resolver.resolve(evidence_input)
        if output.resolution_status not in {"RESOLVED", "RESOLVED_WITH_LIMITATIONS"}:
            raise UserAnswerEvidenceAdapterError(
                f"publication-backed evidence resolution failed closed: {output.sufficiency}"
            )
        evidence_ids = tuple(item.evidence_id for item in output.evidence_packages)
        if not evidence_ids:
            raise UserAnswerEvidenceAdapterError(
                "publication-backed evidence resolution returned no admissible evidence"
            )
        payload = {
            "request_id": output.request_id,
            "resolution_id": output.resolution_id,
            "resolution_status": output.resolution_status,
            "sufficiency": output.sufficiency,
            "evidence_ids": list(evidence_ids),
            "evidence_use": USER_ANSWER,
        }
        return build_raw_intelligence_stage_output(
            execution_id=request.execution_id,
            stage=stage,
            knowledge_snapshot_id=knowledge_snapshot_id,
            output_id=f"{request.execution_id}:published-user-answer-evidence:{output.resolution_id}",
            output_type="publication_backed_evidence_resolution",
            payload=payload,
            evidence_ids=evidence_ids,
            limitations=output.limitations,
        )

    return build_intelligence_stage_adapter(stage=EVIDENCE_STAGE, capability=capability)


__all__ = [
    "EVIDENCE_STAGE",
    "EvidenceInputFactory",
    "UserAnswerEvidenceAdapterError",
    "build_user_answer_evidence_stage_adapter",
]
