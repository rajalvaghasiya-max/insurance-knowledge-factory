"""Governed component-locked rendering pipeline for MO-022G.2."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.semantic_fidelity import (
    ExplanationSemanticContract,
    FidelityRoutingDecision,
    FidelityRoutingPolicy,
    FidelityRoutingResult,
    HumanReviewPacket,
    RuleFamilyCertification,
    SemanticFidelityReport,
)
from insurance_intelligence.evaluation.semantic_fidelity import (
    build_human_review_packet,
    compare_semantics,
    route_fidelity_result,
)
from insurance_intelligence.llm.component_locked import (
    ComponentLockedRenderRequest,
    ParsedComponentLockedOutput,
    VerifiedExplanation,
    assemble_verified_explanation,
    parse_component_locked_output,
    reconstruct_semantics,
)


@dataclass(frozen=True)
class SemanticRenderingOutcome:
    parsed_output: ParsedComponentLockedOutput
    fidelity_report: SemanticFidelityReport
    routing_result: FidelityRoutingResult
    verified_explanation: VerifiedExplanation | None
    human_review_packet: HumanReviewPacket | None


def evaluate_component_locked_rendering(
    contract: ExplanationSemanticContract,
    request: ComponentLockedRenderRequest,
    raw_output: str | dict[str, object],
    policy: FidelityRoutingPolicy,
    certification: RuleFamilyCertification | None,
) -> SemanticRenderingOutcome:
    """Parse, reconstruct, compare, route, and publish only verified meaning."""
    if request.contract_id != contract.contract_id:
        raise ValueError("request contract_id must match contract")
    parsed = parse_component_locked_output(raw_output, request)
    reconstructed = reconstruct_semantics(parsed)
    report = compare_semantics(contract, reconstructed)
    routing = route_fidelity_result(contract, report, policy, certification)

    verified: VerifiedExplanation | None = None
    review: HumanReviewPacket | None = None
    if routing.decision is FidelityRoutingDecision.AUTO_APPROVED:
        verified = assemble_verified_explanation(contract, parsed)
    elif routing.decision is FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED:
        review = build_human_review_packet(contract, report, routing)

    return SemanticRenderingOutcome(
        parsed_output=parsed,
        fidelity_report=report,
        routing_result=routing,
        verified_explanation=verified,
        human_review_packet=review,
    )
