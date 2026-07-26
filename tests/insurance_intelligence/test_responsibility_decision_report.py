from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    DeterministicEvaluationResult,
    EvaluationCase,
    EvaluationCaseCategory,
    EvaluationDisagreement,
    EvaluationDisagreementCategory,
    EvaluationExpectedOutcome,
    EvaluationVerdict,
    LLMResponsibility,
    ResponsibilityDecisionStatus,
)
from insurance_intelligence.evaluation.responsibility import (
    ResponsibilityDecisionError,
    ResponsibilityEvidence,
    build_responsibility_decision,
    build_responsibility_decision_report,
)


def case(
    case_id: str = "case-a",
    responsibility: LLMResponsibility = LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        title=f"Case {case_id}",
        category=EvaluationCaseCategory.KNOWN_GOOD,
        responsibility=responsibility,
        audience="customer",
        governed_evidence_ids=("evidence-1",),
        approved_finding_ids=("finding-1",),
        semantic_requirements=(
            __import__(
                "insurance_intelligence.contracts.llm_evaluation",
                fromlist=["ExpectedSemanticRequirement"],
            ).ExpectedSemanticRequirement(
                requirement_id=f"req-{case_id}",
                component=__import__(
                    "insurance_intelligence.contracts.llm_evaluation",
                    fromlist=["SemanticComponent"],
                ).SemanticComponent.FACT,
                expected_text="Expected fact",
                evidence_ids=("evidence-1",),
            ),
        ),
        forbidden_behaviours=(),
        expected_outcome=EvaluationExpectedOutcome.PASS,
    )


def deterministic(
    case_id: str = "case-a",
    verdict: EvaluationVerdict = EvaluationVerdict.PASSED,
    *,
    limitations: tuple[str, ...] = (),
) -> DeterministicEvaluationResult:
    return DeterministicEvaluationResult(
        result_id=f"det-{case_id}",
        case_id=case_id,
        trace_id=f"trace-{case_id}",
        verdict=verdict,
        passed_check_ids=("check-pass",)
        if verdict is EvaluationVerdict.PASSED
        else (),
        failed_check_ids=("check-fail",)
        if verdict is EvaluationVerdict.FAILED
        else (),
        failure_codes=("UNSUPPORTED_FACT",)
        if verdict is EvaluationVerdict.FAILED
        else (),
        limitations=limitations,
    )


def disagreement(
    case_id: str = "case-a",
    category: EvaluationDisagreementCategory = EvaluationDisagreementCategory.BOTH_PASS,
    *,
    review_required: bool | None = None,
) -> EvaluationDisagreement:
    if review_required is None:
        review_required = category in {
            EvaluationDisagreementCategory.DETERMINISTIC_FAIL_EXTERNAL_PASS,
            EvaluationDisagreementCategory.DETERMINISTIC_PASS_EXTERNAL_FAIL,
            EvaluationDisagreementCategory.INCONCLUSIVE,
        }
    return EvaluationDisagreement(
        disagreement_id=f"dis-{case_id}-{category.value}",
        case_id=case_id,
        trace_id=f"trace-{case_id}",
        deterministic_result_id=f"det-{case_id}",
        external_metric_result_id=f"metric-{case_id}-{category.value}",
        category=category,
        rationale=("comparison",),
        review_required=review_required,
    )


def evidence(
    case_id: str = "case-a",
    *,
    responsibility: LLMResponsibility = LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
    verdict: EvaluationVerdict = EvaluationVerdict.PASSED,
    limitations: tuple[str, ...] = (),
    disagreements: tuple[EvaluationDisagreement, ...] = (),
) -> ResponsibilityEvidence:
    return ResponsibilityEvidence(
        case=case(case_id, responsibility),
        deterministic_result=deterministic(
            case_id,
            verdict,
            limitations=limitations,
        ),
        disagreements=disagreements,
    )


def test_clean_passes_are_approved_for_controlled_use() -> None:
    decision = build_responsibility_decision(
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        evidence_items=(evidence("case-b"), evidence("case-a")),
    )
    assert (
        decision.status
        is ResponsibilityDecisionStatus.APPROVED_FOR_CONTROLLED_USE
    )
    assert decision.evidence_case_ids == ("case-a", "case-b")
    assert decision.required_controls == ()


def test_limitations_require_deterministic_validation_controls() -> None:
    decision = build_responsibility_decision(
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        evidence_items=(
            evidence(
                limitations=("Validate every numerical statement.",),
            ),
        ),
    )
    assert (
        decision.status
        is ResponsibilityDecisionStatus.APPROVED_WITH_DETERMINISTIC_VALIDATION
    )
    assert "Validate every numerical statement." in decision.required_controls
    assert any(
        "authoritative acceptance gate" in control
        for control in decision.required_controls
    )


def test_any_deterministic_failure_rejects_responsibility() -> None:
    decision = build_responsibility_decision(
        responsibility=LLMResponsibility.FACT_EXTRACTION,
        evidence_items=(
            evidence(
                responsibility=LLMResponsibility.FACT_EXTRACTION,
                verdict=EvaluationVerdict.FAILED,
            ),
        ),
    )
    assert decision.status is ResponsibilityDecisionStatus.REJECTED


@pytest.mark.parametrize(
    "verdict",
    [EvaluationVerdict.REQUIRES_REVIEW, EvaluationVerdict.NOT_EVALUATED],
)
def test_unresolved_deterministic_evidence_is_insufficient(
    verdict: EvaluationVerdict,
) -> None:
    decision = build_responsibility_decision(
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        evidence_items=(evidence(verdict=verdict),),
    )
    assert decision.status is ResponsibilityDecisionStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize(
    "category",
    [
        EvaluationDisagreementCategory.DETERMINISTIC_FAIL_EXTERNAL_PASS,
        EvaluationDisagreementCategory.DETERMINISTIC_PASS_EXTERNAL_FAIL,
        EvaluationDisagreementCategory.INCONCLUSIVE,
    ],
)
def test_external_conflict_or_inconclusive_evidence_is_experimental(
    category: EvaluationDisagreementCategory,
) -> None:
    decision = build_responsibility_decision(
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        evidence_items=(
            evidence(disagreements=(disagreement(category=category),)),
        ),
    )
    assert decision.status is ResponsibilityDecisionStatus.EXPERIMENTAL_ONLY


def test_no_evidence_is_not_a_reviewed_responsibility() -> None:
    with pytest.raises(ResponsibilityDecisionError, match="at least one evidence"):
        build_responsibility_decision(
            responsibility=LLMResponsibility.EXAMPLE_GENERATION,
            evidence_items=(),
        )


def test_decision_id_is_stable_and_input_order_independent() -> None:
    first = build_responsibility_decision(
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        evidence_items=(evidence("case-b"), evidence("case-a")),
    )
    second = build_responsibility_decision(
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        evidence_items=(evidence("case-a"), evidence("case-b")),
    )
    assert first.decision_id == second.decision_id


def test_report_returns_requested_responsibilities_in_stable_order() -> None:
    decisions = build_responsibility_decision_report(
        responsibilities=(
            LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
            LLMResponsibility.EXAMPLE_GENERATION,
        ),
        evidence_items=(
            evidence(
                responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
            ),
        ),
    )
    assert [item.responsibility for item in decisions] == [
        LLMResponsibility.PLAIN_LANGUAGE_REPHRASING
    ]


def test_report_does_not_authorize_production_use() -> None:
    decision = build_responsibility_decision(
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        evidence_items=(evidence(),),
    )
    assert any(
        "does not authorize production use" in line
        for line in decision.rationale
    )


def test_mismatched_responsibility_is_rejected() -> None:
    with pytest.raises(ResponsibilityDecisionError, match="responsibility"):
        build_responsibility_decision(
            responsibility=LLMResponsibility.FACT_EXTRACTION,
            evidence_items=(evidence(),),
        )


def test_duplicate_case_ids_are_rejected() -> None:
    with pytest.raises(ResponsibilityDecisionError, match="unique case IDs"):
        build_responsibility_decision(
            responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
            evidence_items=(evidence(), evidence()),
        )


def test_evidence_identity_mismatches_are_rejected() -> None:
    with pytest.raises(ResponsibilityDecisionError, match="case_id"):
        ResponsibilityEvidence(
            case=case("case-a"),
            deterministic_result=deterministic("case-b"),
        )
    with pytest.raises(ResponsibilityDecisionError, match="trace_id"):
        ResponsibilityEvidence(
            case=case("case-a"),
            deterministic_result=deterministic("case-a"),
            disagreements=(
                replace(disagreement("case-a"), trace_id="wrong-trace"),
            ),
        )


def test_duplicate_responsibilities_are_rejected() -> None:
    with pytest.raises(ResponsibilityDecisionError, match="duplicates"):
        build_responsibility_decision_report(
            responsibilities=(
                LLMResponsibility.EXAMPLE_GENERATION,
                LLMResponsibility.EXAMPLE_GENERATION,
            ),
            evidence_items=(),
        )


def test_invalid_collection_types_are_rejected() -> None:
    with pytest.raises(ResponsibilityDecisionError, match="tuple"):
        build_responsibility_decision(
            responsibility=LLMResponsibility.EXAMPLE_GENERATION,
            evidence_items=[],  # type: ignore[arg-type]
        )
    with pytest.raises(ResponsibilityDecisionError, match="tuple"):
        build_responsibility_decision_report(
            responsibilities=[],  # type: ignore[arg-type]
            evidence_items=(),
        )
