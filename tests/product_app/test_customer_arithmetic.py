from decimal import Decimal

from policy_scna_app.customer_arithmetic import (
    build_conditional_percentage_illustration,
    build_difference_illustration,
    build_percentage_illustration,
    difference,
    parse_rupee_amounts,
    percentage_of_amount,
)


def test_percentage_of_amount_is_deterministic() -> None:
    assert percentage_of_amount(
        percentage=Decimal("17.5"),
        amount=Decimal("80000"),
    ) == Decimal("14000.00")


def test_difference_is_deterministic() -> None:
    assert difference(
        larger=Decimal("8500"),
        smaller=Decimal("6000"),
    ) == Decimal("2500.00")


def test_amount_parser_ignores_non_monetary_numbers() -> None:
    assert parse_rupee_amounts("Entry age 61 with 20% co-pay") == ()


def test_percentage_illustration_uses_only_explicit_customer_money() -> None:
    illustration = build_percentage_illustration(
        current_text="If the calculation base is ₹80,000, what is my 17.5% share?",
        prior_customer_texts=(),
        basis_label="the customer-supplied illustration base",
        consequence_boundary="This does not establish policy liability.",
    )

    assert illustration is not None
    assert illustration.result_amount == Decimal("14000.00")
    assert "₹14,000" in illustration.text
    assert "does not establish policy liability" in illustration.text


def test_percentage_illustration_fails_closed_on_multiple_amounts() -> None:
    illustration = build_percentage_illustration(
        current_text="Compare 12% of ₹70,000 with ₹90,000.",
        prior_customer_texts=(),
        basis_label="the customer-supplied illustration base",
        consequence_boundary="This does not establish policy liability.",
    )

    assert illustration is None


def test_conditional_percentage_illustration_calculates_each_explicit_base_without_choosing() -> None:
    illustration = build_conditional_percentage_illustration(
        current_text="The invoice is ₹90,000 but another relevant amount is ₹75,000.",
        prior_customer_texts=("Use an 18% share for this illustration.",),
        consequence_boundary="This does not establish which amount is authoritative.",
    )

    assert illustration is not None
    assert illustration.operation == "CONDITIONAL_PERCENTAGE_OF_AMOUNTS"
    assert "if ₹90,000 is the applicable calculation base, 18% is ₹16,200" in illustration.text
    assert "if ₹75,000 is the applicable calculation base, 18% is ₹13,500" in illustration.text
    assert "not choosing which amount" in illustration.text


def test_conditional_percentage_illustration_fails_closed_with_too_many_bases() -> None:
    illustration = build_conditional_percentage_illustration(
        current_text="Compare ₹70,000, ₹80,000, ₹90,000 and ₹1 lakh.",
        prior_customer_texts=("Use a 12% share for this illustration.",),
        consequence_boundary="This does not establish policy liability.",
    )

    assert illustration is None


def test_difference_uses_prior_customer_percentage_basis() -> None:
    illustration = build_difference_illustration(
        current_text="The room costs ₹8,500 per day. What is the difference?",
        prior_customer_texts=("For illustration, use 2% of ₹3 lakh per day.",),
        prior_percentage_basis_label="the prior customer-supplied basis",
        consequence_boundary="This is not a claim-liability conclusion.",
    )

    assert illustration is not None
    assert illustration.result_amount == Decimal("2500.00")
    assert "₹8,500 minus ₹6,000 is ₹2,500" in illustration.text
    assert "not a claim-liability conclusion" in illustration.text


def test_difference_can_verify_customer_proposed_difference_without_treating_it_as_price() -> None:
    illustration = build_difference_illustration(
        current_text="The room is ₹8,500. Does that mean the difference is ₹2,500?",
        prior_customer_texts=("For illustration, use 2% of ₹3 lakh per day.",),
        prior_percentage_basis_label="the prior customer-supplied basis",
        consequence_boundary="This is not a claim-liability conclusion.",
    )

    assert illustration is not None
    assert illustration.result_amount == Decimal("2500.00")
    assert "₹8,500 minus ₹6,000 is ₹2,500" in illustration.text


def test_difference_fails_closed_when_multiple_larger_amounts_do_not_self_verify() -> None:
    illustration = build_difference_illustration(
        current_text="Compare ₹8,500 with ₹9,500.",
        prior_customer_texts=("For illustration, use 2% of ₹3 lakh per day.",),
        prior_percentage_basis_label="the prior customer-supplied basis",
        consequence_boundary="This is not a claim-liability conclusion.",
    )

    assert illustration is None
