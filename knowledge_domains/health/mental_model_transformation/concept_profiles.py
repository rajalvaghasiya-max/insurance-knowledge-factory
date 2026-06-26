from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MentalModelConceptProfile:
    concept_id: str
    target_belief: str
    target_reasoning: str
    decision_implication: str

    missing_concepts: list[str]
    incorrect_assumptions: list[str]
    incorrect_connections: list[str]
    severity: str

    transformation_type: str
    transformation_steps: list[str]
    recommended_examples: list[str]
    golden_rule: str

    customer_can: list[str]
    advisor_should_confirm: list[str]
    remaining_risks: list[str]

    expected_question: str
    expected_behaviour: str
    observable_success: str

    verification_scenario: dict[str, Any]
    verification_question: str
    verification_correct_answer: str
    verification_common_wrong_answer: str
    verification_why_wrong: str


WAITING_PERIOD_PROFILE = MentalModelConceptProfile(
    concept_id="waiting_period",
    target_belief=(
        "Health-policy coverage is not universally active from day one. "
        "The applicable waiting period depends on the claim type, condition, "
        "benefit, policy start date, and policy terms."
    ),
    target_reasoning=(
        "Initial, specific-disease, and pre-existing disease waiting periods "
        "can be different. A waiting period delays eligible coverage; it is "
        "not automatically a permanent exclusion."
    ),
    decision_implication=(
        "The customer can compare policy options with realistic expectations "
        "about when coverage may begin."
    ),
    missing_concepts=[
        "coverage_activation_timeline",
        "waiting_period_type",
        "waiting_period_vs_exclusion",
    ],
    incorrect_assumptions=[
        "Every illness-related hospitalization is covered immediately after policy purchase.",
        "A waiting period means the condition will never be covered.",
        "One completed waiting period means every condition is covered.",
    ],
    incorrect_connections=[
        "policy_purchase -> universal_day_one_coverage",
        "waiting_period -> permanent_exclusion",
    ],
    severity="high",
    transformation_type="Timeline Correction",
    transformation_steps=[
        "Expose the belief that every health claim is covered from day one.",
        "Separate initial, specific-disease, and pre-existing disease waiting periods.",
        "Show coverage activation using calendar dates rather than only durations.",
        "Explain that a waiting period delays coverage and is not automatically a permanent exclusion.",
        "Verify the customer can identify whether a claim date falls before or after the applicable waiting period.",
    ],
    recommended_examples=[
        "Policy starts on 1 January 2026; initial waiting period ends after 30 days.",
        "Specific-disease waiting period ends after 2 years.",
        "Pre-existing disease waiting period ends after 3 years.",
    ],
    golden_rule=(
        "Before buying a health policy, ask which waiting period applies to you "
        "and on what calendar date that cover becomes active."
    ),
    customer_can=[
        "Explain that different claim types can have different waiting periods.",
        "Distinguish a waiting period from a permanent exclusion.",
        "Identify the policy start date and calculate the relevant coverage activation date.",
        "Ask whether a known condition is subject to a pre-existing disease waiting period.",
    ],
    advisor_should_confirm=[
        "Customer understands that initial, specific-disease, and PED waiting periods can differ.",
        "Customer can state that a waiting period is temporary unless policy wording says otherwise.",
        "Customer has been shown calendar dates for the waiting periods relevant to their situation.",
        "Customer understands that final claim applicability depends on policy wording and condition details.",
    ],
    remaining_risks=[
        "The customer may remember only the shortest waiting period.",
        "The customer may assume a general timeline applies to every condition.",
        "The customer may confuse website summaries with complete contractual wording.",
    ],
    expected_question=(
        "Which waiting period applies to my situation, and on what date does "
        "that coverage become active?"
    ),
    expected_behaviour=(
        "Customer checks applicable waiting periods and calendar dates before "
        "assuming a future claim is covered."
    ),
    observable_success=(
        "Customer can distinguish initial, specific-disease, and PED waiting "
        "periods and identify whether a sample claim date is before or after "
        "coverage activation."
    ),
    verification_scenario={
        "policy_start_date": "2026-01-01",
        "claim_type": "pre_existing_disease",
        "applicable_waiting_period": "3 years",
        "claim_date": "2027-06-01",
    },
    verification_question=(
        "A policy starts on 1 January 2026 and a pre-existing disease has a "
        "3-year waiting period. Is a claim on 1 June 2027 eligible based only "
        "on this waiting-period timeline?"
    ),
    verification_correct_answer=(
        "No. The 3-year waiting period is not complete by 1 June 2027."
    ),
    verification_common_wrong_answer=(
        "Yes. The policy was purchased more than one year ago."
    ),
    verification_why_wrong=(
        "Time since purchase is not enough. The applicable waiting period must "
        "be fully completed for the relevant claim type."
    ),
)


CONCEPT_PROFILES = {
    WAITING_PERIOD_PROFILE.concept_id: WAITING_PERIOD_PROFILE,
}


def get_concept_profile(concept_id: str) -> MentalModelConceptProfile | None:
    return CONCEPT_PROFILES.get(concept_id)