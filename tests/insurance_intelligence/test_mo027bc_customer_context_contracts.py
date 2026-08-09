import pytest

from insurance_intelligence.decision_support.customer_context import (
    ConstraintOperator,
    CustomerCircumstance,
    CustomerContextError,
    CustomerContextProvenance,
    CustomerDecisionContext,
    CustomerHardConstraint,
    CustomerPriority,
    PriorityImportance,
)


SUBJECT = "customer_subject:mother"


def circumstance(*, provenance: CustomerContextProvenance) -> CustomerCircumstance:
    return CustomerCircumstance(
        circumstance_id="insured_entry_age_years",
        subject_reference=SUBJECT,
        value=67,
        provenance=provenance,
        raw_statement="My mother entered at age 67.",
    )


def priority(*, provenance: CustomerContextProvenance) -> CustomerPriority:
    return CustomerPriority(
        priority_id="priority:minimize_claim_time_out_of_pocket",
        dimension_id="claim_time_out_of_pocket",
        importance=PriorityImportance.HIGH,
        provenance=provenance,
        raw_statement="I want to minimize what we pay ourselves during a claim.",
    )


def constraint(*, provenance: CustomerContextProvenance) -> CustomerHardConstraint:
    return CustomerHardConstraint(
        constraint_id="constraint:max_annual_premium",
        dimension_id="quoted_premium",
        operator=ConstraintOperator.LESS_THAN_OR_EQUAL,
        expected_value=30000,
        provenance=provenance,
        raw_statement="My annual premium budget cannot exceed 30000 rupees.",
    )


def context(*, circumstances=(), priorities=(), hard_constraints=()):
    return CustomerDecisionContext(
        context_id="decision_context:family_health:v1",
        subject_references=(SUBJECT,),
        circumstances=tuple(circumstances),
        priorities=tuple(priorities),
        hard_constraints=tuple(hard_constraints),
    )


def test_declared_and_confirmed_values_are_actionable() -> None:
    result = context(
        circumstances=(circumstance(provenance=CustomerContextProvenance.DECLARED),),
        priorities=(priority(provenance=CustomerContextProvenance.CONFIRMED),),
        hard_constraints=(constraint(provenance=CustomerContextProvenance.DECLARED),),
    )

    assert len(result.actionable_circumstances) == 1
    assert len(result.actionable_priorities) == 1
    assert len(result.actionable_hard_constraints) == 1
    assert result.pending_circumstance_confirmations == ()
    assert result.pending_priority_confirmations == ()


def test_inferred_values_are_preserved_but_not_actionable() -> None:
    inferred_circumstance = circumstance(provenance=CustomerContextProvenance.INFERRED)
    inferred_priority = priority(provenance=CustomerContextProvenance.INFERRED)
    inferred_constraint = constraint(provenance=CustomerContextProvenance.INFERRED)

    result = context(
        circumstances=(inferred_circumstance,),
        priorities=(inferred_priority,),
        hard_constraints=(inferred_constraint,),
    )

    assert result.actionable_circumstances == ()
    assert result.actionable_priorities == ()
    assert result.actionable_hard_constraints == ()
    assert result.pending_circumstance_confirmations == (inferred_circumstance,)
    assert result.pending_priority_confirmations == (inferred_priority,)


def test_circumstance_and_priority_are_distinct_contracts() -> None:
    c = circumstance(provenance=CustomerContextProvenance.DECLARED)
    p = priority(provenance=CustomerContextProvenance.DECLARED)

    assert type(c) is CustomerCircumstance
    assert type(p) is CustomerPriority
    assert "importance" not in c.__dataclass_fields__
    assert "value" not in p.__dataclass_fields__
    assert "subject_reference" not in p.__dataclass_fields__


def test_hard_constraint_is_explicit_rule_not_priority_weight() -> None:
    item = constraint(provenance=CustomerContextProvenance.DECLARED)
    assert item.operator is ConstraintOperator.LESS_THAN_OR_EQUAL
    assert item.expected_value == 30000
    assert "importance" not in item.__dataclass_fields__
    assert "weight" not in item.__dataclass_fields__


def test_context_rejects_circumstance_for_unknown_subject() -> None:
    other = CustomerCircumstance(
        circumstance_id="insured_entry_age_years",
        subject_reference="customer_subject:father",
        value=65,
        provenance=CustomerContextProvenance.DECLARED,
        raw_statement="My father is 65.",
    )
    with pytest.raises(CustomerContextError, match="outside the decision context"):
        context(circumstances=(other,))


def test_context_rejects_duplicate_subject_circumstance_pairs() -> None:
    first = circumstance(provenance=CustomerContextProvenance.DECLARED)
    second = CustomerCircumstance(
        circumstance_id=first.circumstance_id,
        subject_reference=first.subject_reference,
        value=68,
        provenance=CustomerContextProvenance.CONFIRMED,
        raw_statement="Correction: entry age was 68.",
    )
    with pytest.raises(CustomerContextError, match="duplicate subject/circumstance"):
        context(circumstances=(first, second))


def test_context_rejects_duplicate_priority_ids() -> None:
    first = priority(provenance=CustomerContextProvenance.DECLARED)
    second = CustomerPriority(
        priority_id=first.priority_id,
        dimension_id="quoted_premium",
        importance=PriorityImportance.MEDIUM,
        provenance=CustomerContextProvenance.CONFIRMED,
        raw_statement="Premium matters too.",
    )
    with pytest.raises(CustomerContextError, match="duplicate priority ids"):
        context(priorities=(first, second))


def test_in_constraint_requires_non_empty_tuple() -> None:
    with pytest.raises(CustomerContextError, match="non-empty tuple"):
        CustomerHardConstraint(
            constraint_id="constraint:network_city",
            dimension_id="network_access",
            operator=ConstraintOperator.IN,
            expected_value=(),
            provenance=CustomerContextProvenance.DECLARED,
            raw_statement="The hospital must be in one of my acceptable locations.",
        )


def test_customer_context_has_no_recommendation_or_aggregation_fields() -> None:
    forbidden = {
        "score",
        "overall_score",
        "weight",
        "winner",
        "recommendation",
        "suitability",
        "preferred_product",
        "net_direction",
        "lean",
    }
    assert forbidden.isdisjoint(CustomerCircumstance.__dataclass_fields__)
    assert forbidden.isdisjoint(CustomerPriority.__dataclass_fields__)
    assert forbidden.isdisjoint(CustomerHardConstraint.__dataclass_fields__)
    assert forbidden.isdisjoint(CustomerDecisionContext.__dataclass_fields__)
