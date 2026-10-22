from decimal import Decimal

from policy_scna_app.customer_arithmetic import (
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
