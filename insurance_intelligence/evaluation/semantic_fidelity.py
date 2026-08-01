"""Deterministic semantic comparison and governed production routing for MO-022G."""
from __future__ import annotations

from hashlib import sha256

from insurance_intelligence.contracts.semantic_fidelity import (
    CanonicalSemanticComponent,
    CertificationStatus,
    ExplanationSemanticContract,
    FidelityRoutingDecision,
    FidelityRoutingPolicy,
    FidelityRoutingResult,
    HumanReviewPacket,
    ReconstructedSemanticComponent,
    RuleFamilyCertification,
    SemanticAttribute,
    SemanticComparisonStatus,
    SemanticComponentComparison,
    SemanticFidelityReport,
    SemanticRiskTier,
)


class SemanticFidelityError(ValueError):
    """Raised when semantic comparison inputs are inconsistent."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _attribute_map(attributes: tuple[SemanticAttribute, ...]) -> dict[str, object]:
    return {item.name: item.value for item in attributes}


def _mismatch_codes(
    expected: CanonicalSemanticComponent,
    observed: ReconstructedSemanticComponent,
) -> tuple[str, ...]:
    codes: list[str] = []
    if expected.kind is not observed.kind:
        codes.append("SEMANTIC_KIND_CHANGED")

    expected_map = _attribute_map(expected.attributes)
    observed_map = _attribute_map(observed.attributes)

    missing_names = sorted(set(expected_map) - set(observed_map))
    surplus_names = sorted(set(observed_map) - set(expected_map))
    if missing_names:
        codes.append("SEMANTIC_ATTRIBUTE_MISSING")
    if surplus_names:
        codes.append("UNSUPPORTED_SEMANTIC_ADDITION")

    for name in sorted(set(expected_map).intersection(observed_map)):
        expected_value = expected_map[name]
        observed_value = observed_map[name]
        if expected_value == observed_value:
            continue
        if isinstance(expected_value, tuple) or isinstance(observed_value, tuple):
            codes.append("SEMANTIC_SET_MISMATCH")
        elif name in {"operator", "logical_operator", "certainty", "polarity"}:
            codes.append("SEMANTIC_LOGIC_CHANGED")
        elif isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool):
            codes.append("EXACT_VALUE_CHANGED")
        else:
            codes.append("SEMANTIC_VALUE_CHANGED")

    return tuple(dict.fromkeys(codes))


def compare_semantics(
    contract: ExplanationSemanticContract,
    reconstructed: tuple[ReconstructedSemanticComponent, ...],
    *,
    report_id: str | None = None,
) -> SemanticFidelityReport:
    """Compare reconstructed meaning with the approved contract using exact invariants."""
    if not isinstance(contract, ExplanationSemanticContract):
        raise TypeError("contract must be an ExplanationSemanticContract")
    if not isinstance(reconstructed, tuple):
        raise TypeError("reconstructed must be a tuple")
    if not all(isinstance(item, ReconstructedSemanticComponent) for item in reconstructed):
        raise TypeError("reconstructed must contain ReconstructedSemanticComponent values")

    observed_ids = tuple(item.component_id for item in reconstructed)
    if len(observed_ids) != len(set(observed_ids)):
        raise SemanticFidelityError("reconstructed component IDs must be unique")

    expected_by_id = {item.component_id: item for item in contract.components}
    observed_by_id = {item.component_id: item for item in reconstructed}
    comparisons: list[SemanticComponentComparison] = []
    hard_failures: list[str] = []
    unresolved_ids: list[str] = []

    for component in contract.components:
        observed = observed_by_id.get(component.component_id)
        if observed is None:
            status = (
                SemanticComparisonStatus.MISSING
                if component.required
                else SemanticComparisonStatus.MATCHED
            )
            codes = ("SEMANTIC_OMISSION",) if component.required else ()
            if codes:
                hard_failures.extend(codes)
            comparisons.append(
                SemanticComponentComparison(
                    component_id=component.component_id,
                    status=status,
                    risk_tier=component.risk_tier,
                    mismatch_codes=codes,
                    expected_attributes=component.attributes,
                    observed_attributes=(),
                )
            )
            continue

        if observed.unresolved_reasons:
            codes = ("SEMANTIC_EXTRACTION_UNRESOLVED",)
            unresolved_ids.append(component.component_id)
            comparisons.append(
                SemanticComponentComparison(
                    component_id=component.component_id,
                    status=SemanticComparisonStatus.UNRESOLVED,
                    risk_tier=component.risk_tier,
                    mismatch_codes=codes,
                    expected_attributes=component.attributes,
                    observed_attributes=observed.attributes,
                    confidence=observed.confidence,
                    extractor_agreement=observed.extractor_agreement,
                )
            )
            continue

        codes = _mismatch_codes(component, observed)
        status = (
            SemanticComparisonStatus.MATCHED
            if not codes
            else SemanticComparisonStatus.MISMATCHED
        )
        if codes:
            hard_failures.extend(codes)
        comparisons.append(
            SemanticComponentComparison(
                component_id=component.component_id,
                status=status,
                risk_tier=component.risk_tier,
                mismatch_codes=codes,
                expected_attributes=component.attributes,
                observed_attributes=observed.attributes,
                confidence=observed.confidence,
                extractor_agreement=observed.extractor_agreement,
            )
        )

    for component_id in sorted(set(observed_by_id) - set(expected_by_id)):
        observed = observed_by_id[component_id]
        codes = ("UNSUPPORTED_SEMANTIC_ADDITION",)
        hard_failures.extend(codes)
        comparisons.append(
            SemanticComponentComparison(
                component_id=component_id,
                status=SemanticComparisonStatus.SURPLUS,
                risk_tier=SemanticRiskTier.RULE_LOGIC,
                mismatch_codes=codes,
                expected_attributes=(),
                observed_attributes=observed.attributes,
                confidence=observed.confidence,
                extractor_agreement=observed.extractor_agreement,
            )
        )

    comparisons.sort(key=lambda item: item.component_id)
    resolved_report_id = report_id or _stable_id(
        "semantic-report",
        contract.contract_id,
        tuple(
            (
                item.component_id,
                item.status.value,
                item.mismatch_codes,
                item.confidence,
                item.extractor_agreement,
            )
            for item in comparisons
        ),
    )
    return SemanticFidelityReport(
        report_id=resolved_report_id,
        contract_id=contract.contract_id,
        comparisons=tuple(comparisons),
        hard_failure_codes=tuple(sorted(set(hard_failures))),
        unresolved_component_ids=tuple(sorted(set(unresolved_ids))),
    )


def route_fidelity_result(
    contract: ExplanationSemanticContract,
    report: SemanticFidelityReport,
    policy: FidelityRoutingPolicy,
    certification: RuleFamilyCertification | None,
    *,
    routing_id: str | None = None,
) -> FidelityRoutingResult:
    """Route verified meaning to auto-approval, review, rejection, or system error."""
    if report.contract_id != contract.contract_id:
        raise SemanticFidelityError("report contract_id must match contract")

    reasons: list[str] = []
    decision: FidelityRoutingDecision

    if report.hard_failure_codes:
        decision = FidelityRoutingDecision.AUTO_REJECTED
        reasons.extend(report.hard_failure_codes)
    elif report.unresolved_component_ids:
        decision = FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
        reasons.append("SEMANTIC_PROOF_INCOMPLETE")
    else:
        low_confidence = tuple(
            item.component_id
            for item in report.comparisons
            if item.status is SemanticComparisonStatus.MATCHED
            and item.confidence is not None
            and item.confidence < policy.minimum_confidence
        )
        low_agreement = tuple(
            item.component_id
            for item in report.comparisons
            if item.status is SemanticComparisonStatus.MATCHED
            and item.extractor_agreement is not None
            and item.extractor_agreement < policy.minimum_extractor_agreement
        )
        if low_confidence:
            reasons.append("LOW_EXTRACTION_CONFIDENCE")
        if low_agreement:
            reasons.append("LOW_EXTRACTOR_AGREEMENT")

        certification_ok = (
            certification is not None
            and certification.rule_family == contract.rule_family
            and certification.status is CertificationStatus.CERTIFIED
        )
        if policy.require_certified_rule_family and not certification_ok:
            reasons.append("RULE_FAMILY_NOT_CERTIFIED")

        if reasons:
            decision = FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED
        else:
            decision = FidelityRoutingDecision.AUTO_APPROVED
            reasons.append("SEMANTIC_FIDELITY_VERIFIED")

    resolved_routing_id = routing_id or _stable_id(
        "fidelity-routing",
        report.report_id,
        policy.policy_id,
        certification.certification_id if certification else "none",
        decision.value,
        tuple(reasons),
    )
    return FidelityRoutingResult(
        routing_id=resolved_routing_id,
        decision=decision,
        reason_codes=tuple(dict.fromkeys(reasons)),
        report_id=report.report_id,
        certification_id=(certification.certification_id if certification else None),
    )


def build_human_review_packet(
    contract: ExplanationSemanticContract,
    report: SemanticFidelityReport,
    routing: FidelityRoutingResult,
    *,
    review_packet_id: str | None = None,
) -> HumanReviewPacket:
    """Build the minimal governed evidence packet for a human-review decision."""
    if routing.decision is not FidelityRoutingDecision.HUMAN_REVIEW_REQUIRED:
        raise SemanticFidelityError(
            "human review packets require HUMAN_REVIEW_REQUIRED routing"
        )
    if routing.report_id != report.report_id or report.contract_id != contract.contract_id:
        raise SemanticFidelityError("contract, report, and routing identities must align")

    review_components = tuple(
        item.component_id
        for item in report.comparisons
        if item.status is not SemanticComparisonStatus.MATCHED
        or (
            item.confidence is not None
            and item.confidence < 1.0
        )
        or (
            item.extractor_agreement is not None
            and item.extractor_agreement < 1.0
        )
    )
    if not review_components:
        review_components = tuple(item.component_id for item in report.comparisons)

    evidence_by_component = {
        item.component_id: item.evidence_ids for item in contract.components
    }
    evidence_ids = tuple(
        dict.fromkeys(
            evidence_id
            for component_id in review_components
            for evidence_id in evidence_by_component.get(component_id, ())
        )
    )
    resolved_packet_id = review_packet_id or _stable_id(
        "human-review",
        contract.contract_id,
        report.report_id,
        routing.routing_id,
        review_components,
        routing.reason_codes,
    )
    return HumanReviewPacket(
        review_packet_id=resolved_packet_id,
        contract_id=contract.contract_id,
        report_id=report.report_id,
        routing_id=routing.routing_id,
        component_ids=review_components,
        reason_codes=routing.reason_codes,
        evidence_ids=evidence_ids,
    )
