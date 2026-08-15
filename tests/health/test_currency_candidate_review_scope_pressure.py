from knowledge_domains.health.extraction_primitives.currency_candidate_review import CurrencyCandidateReview


def _candidate(text: str, value: int, raw_text: str) -> dict:
    return {
        "normalized_value": {
            "kind": "currency",
            "value": value,
            "unit": "INR",
            "raw_text": raw_text,
        },
        "evidence": {"text": text},
    }


def test_air_ambulance_scope_is_inferred_from_bounded_evidence():
    candidate = _candidate(
        "Air ambulance service up to Rs.2,50,000/- per hospitalization not exceeding Rs.5,00,000/- per Policy Period",
        250000,
        "Rs.2,50,000",
    )
    scope = CurrencyCandidateReview._infer_scope(candidate)
    assert scope["benefit_scope_key"] == "air_ambulance"


def test_home_care_scope_is_inferred_from_bounded_evidence():
    candidate = _candidate(
        "10. Home Care Treatment: Payable up to 10% of the Sum Insured subject to maximum of Rs. 5,00,000 in a Policy Year",
        500000,
        "Rs. 5,00,000",
    )
    scope = CurrencyCandidateReview._infer_scope(candidate)
    assert scope["benefit_scope_key"] == "home_care_treatment"


def test_cumulative_bonus_scope_is_inferred_from_bounded_evidence():
    candidate = _candidate(
        "12. Cumulative Bonus: Where the Sum Insured under the policy is Rs.5,00,000, the Insured Person would be entitled to the benefit",
        500000,
        "Rs.5,00,000",
    )
    scope = CurrencyCandidateReview._infer_scope(candidate)
    assert scope["benefit_scope_key"] == "cumulative_bonus"


def test_bariatric_scope_hint_does_not_resolve_table_binding():
    candidate = _candidate(
        "Bariatric surgical procedure and its complications are payable subject to limits mentioned in the table given below. This maximum limit of Rs.2,50,000 is inclusive of pre-hospitalization expenses.",
        250000,
        "Rs.2,50,000",
    )
    scope = CurrencyCandidateReview._infer_scope(candidate)
    assert scope["benefit_scope_key"] == "bariatric_surgery"
    flags = CurrencyCandidateReview._review_flags(
        [{"evidence": {"text": candidate["evidence"]["text"], "page_number": 1}}],
        ["sub_limit_or_limit"],
        [],
        {**scope, "scope_inference_requires_review": True},
    )
    assert "table_layout_binding_possible" in flags


def test_compassionate_visit_scope_is_inferred_from_named_clause():
    candidate = _candidate(
        "C.13.12 Compassionate Visit On availing this Optional Cover, the cost of two way economy class air ticket or travel fare up to maximum of INR 50,000/- as specified in Policy Schedule will be reimbursed.",
        50000,
        "INR 50,000",
    )
    scope = CurrencyCandidateReview._infer_scope(candidate)
    assert scope["benefit_scope_key"] == "compassionate_visit"


def test_advanced_health_checkup_scope_is_inferred_without_resolving_band_binding():
    candidate = _candidate(
        "Advanced Health Check-up (90 days waiting period) Combined Sub-limit of INR 5 Lacs or up to SI, whichever is lower",
        500000,
        "INR 5 Lacs",
    )
    scope = CurrencyCandidateReview._infer_scope(candidate)
    assert scope["benefit_scope_key"] == "advanced_health_checkup"


def test_unknown_scope_remains_unresolved():
    candidate = _candidate(
        "Dependent Children and persons above 70 years can be covered under this Section up to the Sum Insured of Rs.10,00,000.",
        1000000,
        "Rs.10,00,000",
    )
    scope = CurrencyCandidateReview._infer_scope(candidate)
    assert scope["benefit_scope_key"] == "scope_unresolved"
