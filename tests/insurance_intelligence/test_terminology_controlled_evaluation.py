from dataclasses import replace
from datetime import date

from insurance_intelligence.contracts.terminology import (
    TerminologyPublicationStatus,
    TerminologyReviewStatus,
)
from insurance_intelligence.evaluation.terminology_controlled_evaluation import (
    CONTROLLED_TERMINOLOGY_CASES,
    run_controlled_terminology_evaluation,
)
from insurance_intelligence.orchestration.terminology_gate import (
    TerminologyOrchestrationGate,
    TerminologyOrchestrationRequest,
)
from insurance_intelligence.terminology.alias_resolver import (
    ExactAliasTerminologyResolver,
)
from insurance_intelligence.terminology.context_resolver import (
    ContextualTerminologyResolver,
)
from insurance_intelligence.terminology.registry import TerminologyRegistrySnapshot
from insurance_intelligence.terminology.star_comprehensive_catalogue import (
    STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,
    STAR_COMPREHENSIVE_COPAYMENT_TERM,
    build_star_comprehensive_copayment_snapshot,
)

AS_OF = date(2026, 7, 30)
VARIANT = "pv_star_health_star_comprehensive_shahlip26044v092526"


def test_controlled_pack_covers_ready_and_blocked_paths() -> None:
    report = run_controlled_terminology_evaluation(as_of=AS_OF)

    assert report.passed
    assert len(report.observations) == len(CONTROLLED_TERMINOLOGY_CASES)
    assert {item.status for item in report.observations} == {"READY", "BLOCKED"}
    assert all(item.may_advance for item in report.observations if item.status == "READY")
    assert all(not item.may_advance for item in report.observations if item.status == "BLOCKED")


def test_controlled_pack_is_deterministic() -> None:
    first = run_controlled_terminology_evaluation(as_of=AS_OF)
    second = run_controlled_terminology_evaluation(as_of=AS_OF)

    assert first == second
    assert first.evaluation_id == second.evaluation_id
    assert tuple(item.fingerprint for item in first.observations) == tuple(
        item.fingerprint for item in second.observations
    )


def test_ready_cases_share_the_same_governed_concept_and_implementation() -> None:
    report = run_controlled_terminology_evaluation(as_of=AS_OF)
    ready = tuple(item for item in report.observations if item.status == "READY")

    assert {item.canonical_concept_family_id for item in ready} == {
        "health:cost_sharing:copayment"
    }
    assert len({item.product_term_implementation_id for item in ready}) == 1


def test_blocked_cases_never_receive_canonical_handoff() -> None:
    report = run_controlled_terminology_evaluation(as_of=AS_OF)

    for observation in report.observations:
        if observation.status == "BLOCKED":
            assert observation.canonical_concept_family_id is None
            assert observation.product_term_implementation_id is None
            assert observation.reason_codes


def _gate_for_terms(terms, implementations) -> TerminologyOrchestrationGate:
    base = build_star_comprehensive_copayment_snapshot()
    snapshot = TerminologyRegistrySnapshot(
        marketing_terms=tuple(terms),
        implementations=tuple(implementations),
        concepts=base.concepts,
        alias_candidates=(),
    )
    return TerminologyOrchestrationGate(
        resolver=ContextualTerminologyResolver(
            resolver=ExactAliasTerminologyResolver(
                resolver=snapshot.build_resolver(),
                aliases=(),
            )
        )
    )


def _request() -> TerminologyOrchestrationRequest:
    return TerminologyOrchestrationRequest(
        request_id="eval:governance",
        text="Co-payment",
        insurer_id="star_health",
        product_id="star_comprehensive",
        product_variant_id=VARIANT,
    )


def test_ambiguous_governed_terms_block_orchestration() -> None:
    second_term = replace(
        STAR_COMPREHENSIVE_COPAYMENT_TERM,
        term_id="term:star_health:star_comprehensive:copayment:second",
    )
    second_implementation = replace(
        STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,
        implementation_id="implementation:star_health:star_comprehensive:copayment:second",
        term_id=second_term.term_id,
    )
    gate = _gate_for_terms(
        (STAR_COMPREHENSIVE_COPAYMENT_TERM, second_term),
        (STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION, second_implementation),
    )

    result = gate.evaluate(_request(), as_of=AS_OF)

    assert result.status == "BLOCKED"
    assert result.may_advance is False
    assert result.reason_codes == ("AMBIGUOUS_GOVERNED_TERMINOLOGY",)
    assert result.canonical_context == {}


def test_unpublished_term_is_excluded_and_blocks() -> None:
    unpublished = replace(
        STAR_COMPREHENSIVE_COPAYMENT_TERM,
        review_status=TerminologyReviewStatus.REVIEW_REQUIRED,
        publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
    )
    gate = _gate_for_terms(
        (unpublished,),
        (STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,),
    )

    result = gate.evaluate(_request(), as_of=AS_OF)

    assert result.status == "BLOCKED"
    assert result.may_advance is False
    assert result.reason_codes == ("NO_GOVERNED_TERM_OR_ALIAS_MATCH",)


def test_inactive_term_is_excluded_and_blocks() -> None:
    inactive = replace(
        STAR_COMPREHENSIVE_COPAYMENT_TERM,
        effective_from=date(2027, 1, 1),
    )
    gate = _gate_for_terms(
        (inactive,),
        (STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,),
    )

    result = gate.evaluate(_request(), as_of=AS_OF)

    assert result.status == "BLOCKED"
    assert result.may_advance is False
    assert result.reason_codes == ("NO_GOVERNED_TERM_OR_ALIAS_MATCH",)


def test_evaluation_id_changes_when_as_of_date_changes() -> None:
    first = run_controlled_terminology_evaluation(as_of=AS_OF)
    second = run_controlled_terminology_evaluation(as_of=date(2026, 7, 31))

    assert first.evaluation_id != second.evaluation_id
