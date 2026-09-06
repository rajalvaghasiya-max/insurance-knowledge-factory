"""Deterministic evaluator for governed publication decisions (P2.3)."""

from __future__ import annotations

from insurance_intelligence.contracts.publication_decision import (
    PublicationDecisionInput,
    PublicationDecisionResult,
)
from insurance_intelligence.publication_decision.authorization import (
    PublicationBoundaryAuthorizationError,
    resolve_authorized_certification_limitations,
)


class PublicationDecisionEvaluationError(ValueError):
    """Raised when publication evaluation cannot be performed safely."""


def _contains_boundary(limitations: tuple[str, ...], token: str) -> bool:
    normalized = token.casefold()
    return any(normalized in item.casefold() for item in limitations)


def evaluate_publication_decision(
    decision_input: PublicationDecisionInput,
) -> PublicationDecisionResult:
    """Evaluate an explicit publication request against certification outputs.

    The evaluator does not publish anything. It derives only an explicit PUBLISH,
    WITHHOLD or BLOCKED decision and always records that no authoritative publication
    has been created. Historical certification limitations remain immutable; a supported
    publication-state limitation may become non-effective only through an exact explicit
    boundary authorization carried on the input.
    """
    if not isinstance(decision_input, PublicationDecisionInput):
        raise PublicationDecisionEvaluationError(
            "decision_input must be a PublicationDecisionInput"
        )

    certification = decision_input.certification_result
    try:
        effective_certification_limitations, resolved_certification_limitations = (
            resolve_authorized_certification_limitations(
                certification=certification,
                authorization=decision_input.boundary_authorization,
            )
        )
    except PublicationBoundaryAuthorizationError as exc:
        raise PublicationDecisionEvaluationError(str(exc)) from exc

    failures: list[str] = []
    missing_limitations = tuple(
        item
        for item in effective_certification_limitations
        if item not in decision_input.limitations
    )
    if missing_limitations:
        failures.append("Certification limitations were not fully preserved.")

    if not certification.trace_references:
        failures.append("Certification trace references are required.")
    if not decision_input.evidence_trace_references:
        failures.append("Evidence trace references are required.")

    if certification.outcome in {"FAIL", "BLOCKED"}:
        decision_status = "BLOCKED"
        failures.append(
            f"Certification outcome {certification.outcome} cannot proceed to publication."
        )
    elif decision_input.requested_status == "BLOCKED":
        decision_status = "BLOCKED"
    elif decision_input.requested_status == "WITHHOLD":
        decision_status = "WITHHOLD"
    else:
        if _contains_boundary(decision_input.limitations, "bound_not_published"):
            failures.append("bound_not_published must be resolved before publication.")
        decision_status = "BLOCKED" if failures else "PUBLISH"

    if failures and decision_status == "WITHHOLD":
        decision_status = "BLOCKED"

    authorization = decision_input.boundary_authorization
    return PublicationDecisionResult(
        contract_version=decision_input.contract_version,
        decision_id=decision_input.decision_id,
        governed_subject_reference=decision_input.governed_subject_reference,
        certification_id=certification.certification_id,
        certification_outcome=certification.outcome,
        topic_id=certification.topic_id,
        topic_version=certification.topic_version,
        requested_status=decision_input.requested_status,
        decision_status=decision_status,
        decision_reasons=decision_input.decision_reasons,
        limitations=decision_input.limitations,
        certification_trace_references=certification.trace_references,
        evidence_trace_references=decision_input.evidence_trace_references,
        decision_authority=decision_input.decision_authority,
        publication_permitted=decision_status == "PUBLISH",
        authoritative_publication_created=False,
        failures=tuple(failures),
        resolved_certification_limitations=resolved_certification_limitations,
        authorization_id=(authorization.authorization_id if authorization is not None else None),
        authorization_trace_references=(
            authorization.trace_references if authorization is not None else ()
        ),
    )
