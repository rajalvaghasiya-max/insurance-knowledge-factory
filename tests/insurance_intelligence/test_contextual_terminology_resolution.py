from dataclasses import replace
from datetime import date

import pytest

from insurance_intelligence.terminology.alias_resolver import (
    ExactAliasTerminologyResolver,
)
from insurance_intelligence.terminology.context_resolver import (
    ContextualTerminologyResolver,
    TerminologyContextError,
    TerminologyContextQuery,
)
from insurance_intelligence.terminology.registry import TerminologyRegistrySnapshot
from insurance_intelligence.terminology.star_comprehensive_aliases import (
    build_star_comprehensive_alias_resolver,
)
from insurance_intelligence.terminology.star_comprehensive_catalogue import (
    STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,
    STAR_COMPREHENSIVE_COPAYMENT_TERM,
    build_star_comprehensive_copayment_snapshot,
)

_AS_OF = date(2026, 7, 30)
_VARIANT = "pv_star_health_star_comprehensive_shahlip26044v092526"


def _resolver() -> ContextualTerminologyResolver:
    return ContextualTerminologyResolver(
        resolver=build_star_comprehensive_alias_resolver()
    )


def test_resolves_direct_term_with_complete_context() -> None:
    outcome = _resolver().resolve(
        TerminologyContextQuery(
            text="Co-payment",
            insurer_id="star_health",
            product_id="star_comprehensive",
            product_variant_id=_VARIANT,
        ),
        as_of=_AS_OF,
    )

    assert outcome.is_resolved
    assert outcome.result is not None
    assert outcome.result.term.term_id == STAR_COMPREHENSIVE_COPAYMENT_TERM.term_id
    assert outcome.result.selected_concept is not None
    assert outcome.result.selected_concept.concept_family_id == "health:cost_sharing:copayment"


def test_resolves_exact_alias_with_complete_context() -> None:
    outcome = _resolver().resolve(
        TerminologyContextQuery(
            text="  COPAY  ",
            insurer_id="star_health",
            product_id="star_comprehensive",
            product_variant_id=_VARIANT,
        ),
        as_of=_AS_OF,
    )

    assert outcome.is_resolved
    assert outcome.result is not None
    assert outcome.result.term.display_name == "Co-payment"


def test_missing_context_is_explicit_and_fail_closed() -> None:
    outcome = _resolver().resolve(
        TerminologyContextQuery(text="Copay"),
        as_of=_AS_OF,
    )

    assert not outcome.is_resolved
    assert outcome.reason_codes == ("MISSING_REQUIRED_PRODUCT_CONTEXT",)
    assert outcome.missing_context == (
        "insurer_id",
        "product_id",
        "product_variant_id",
    )
    assert outcome.candidate_term_ids == (
        STAR_COMPREHENSIVE_COPAYMENT_TERM.term_id,
    )


def test_partial_context_remains_unresolved() -> None:
    outcome = _resolver().resolve(
        TerminologyContextQuery(
            text="Co payment",
            insurer_id="star_health",
            product_id="star_comprehensive",
        ),
        as_of=_AS_OF,
    )

    assert outcome.reason_codes == ("MISSING_REQUIRED_PRODUCT_CONTEXT",)
    assert outcome.missing_context == ("product_variant_id",)


def test_wrong_context_does_not_reuse_product_alias() -> None:
    outcome = _resolver().resolve(
        TerminologyContextQuery(
            text="Copay",
            insurer_id="star_health",
            product_id="another_product",
            product_variant_id=_VARIANT,
        ),
        as_of=_AS_OF,
    )

    assert not outcome.is_resolved
    assert outcome.reason_codes == ("NO_GOVERNED_MATCH_FOR_CONTEXT",)


def test_unknown_text_is_not_corrected_or_inferred() -> None:
    outcome = _resolver().resolve(
        TerminologyContextQuery(
            text="co/pay",
            insurer_id="star_health",
            product_id="star_comprehensive",
            product_variant_id=_VARIANT,
        ),
        as_of=_AS_OF,
    )

    assert outcome.reason_codes == ("NO_GOVERNED_TERM_OR_ALIAS_MATCH",)
    assert outcome.candidate_term_ids == ()


def test_multiple_governed_terms_in_same_context_are_ambiguous() -> None:
    second_term = replace(
        STAR_COMPREHENSIVE_COPAYMENT_TERM,
        term_id="term:star_health:star_comprehensive:copayment:second",
    )
    second_implementation = replace(
        STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,
        implementation_id="implementation:star_health:star_comprehensive:copayment:second",
        term_id=second_term.term_id,
    )
    base = build_star_comprehensive_copayment_snapshot()
    snapshot = TerminologyRegistrySnapshot(
        marketing_terms=(STAR_COMPREHENSIVE_COPAYMENT_TERM, second_term),
        implementations=(
            STAR_COMPREHENSIVE_COPAYMENT_IMPLEMENTATION,
            second_implementation,
        ),
        concepts=base.concepts,
        alias_candidates=(),
    )
    resolver = ContextualTerminologyResolver(
        resolver=ExactAliasTerminologyResolver(
            resolver=snapshot.build_resolver(),
            aliases=(),
        )
    )

    outcome = resolver.resolve(
        TerminologyContextQuery(
            text="Co-payment",
            insurer_id="star_health",
            product_id="star_comprehensive",
            product_variant_id=_VARIANT,
        ),
        as_of=_AS_OF,
    )

    assert not outcome.is_resolved
    assert outcome.reason_codes == ("AMBIGUOUS_GOVERNED_TERMINOLOGY",)
    assert outcome.candidate_term_ids == tuple(
        sorted(
            (
                STAR_COMPREHENSIVE_COPAYMENT_TERM.term_id,
                second_term.term_id,
            )
        )
    )


def test_query_rejects_blank_supplied_context() -> None:
    with pytest.raises(TerminologyContextError, match="insurer_id"):
        TerminologyContextQuery(text="Copay", insurer_id="   ")
