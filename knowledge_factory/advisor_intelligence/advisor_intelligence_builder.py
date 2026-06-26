from .advisor_intelligence_models import (
    AdvisorIntelligenceAsset,
    CustomerPsychology,
    DecisionPsychology,
    StorytellingAsset,
    VerificationQuestion,
    AdvisorConfidence,
    AdvisorIntelligenceCertification,
)


def build_advisor_intelligence_asset(concept_id: str) -> AdvisorIntelligenceAsset:
    if concept_id != "copay":
        raise ValueError(f"Unsupported concept_id for AIA-001B: {concept_id}")

    return AdvisorIntelligenceAsset(
        asset_id="",
        concept_id="copay",
        concept_name="Copay",
        version="1.0",
        customer_psychology=CustomerPsychology(
            visible_focus="lower premium",
            hidden_concern="affordability",
            blind_spot="claim-stage liability",
            confidence_level="optimistic",
            typical_assumption="hospitalization is unlikely",
        ),
        decision_psychology=DecisionPsychology(
            biases=["present_bias", "optimism_bias", "premium_anchoring"],
            decision_pattern="save now, pay later",
        ),
        common_objections=[
            "Why should I pay extra for no-copay?",
            "I rarely get hospitalized.",
            "I already have company insurance.",
            "Premium difference seems too high.",
            "I can manage a small copay if needed.",
        ],
        advisor_objective=(
            "Help the customer understand the future financial consequences "
            "of today's premium-saving decision."
        ),
        response_pattern=[
            "Acknowledge the premium concern.",
            "Explain claim-stage impact.",
            "Show financial outcome simulation.",
            "Explain the trade-off.",
            "Verify understanding.",
        ],
        storytelling_asset=StorytellingAsset(
            title="The ₹4,000 Premium Saving",
            scenario="Customer selected Copay to save ₹4,000 annual premium.",
            outcome="Hospitalization resulted in ₹95,000 customer contribution.",
            lesson="Small premium savings can create large claim liabilities.",
        ),
        trust_builders=[
            "Show actual claim simulation.",
            "Explain disadvantages honestly.",
            "Compare both options.",
            "Avoid one-sided recommendations.",
            "Provide written summary.",
        ],
        warning_signals=[
            "Customer only discusses premium.",
            "Customer ignores claim examples.",
            "Customer cannot explain admissible claim.",
            "Customer focuses only on best-case outcomes.",
        ],
        verification=VerificationQuestion(
            question="What is the trade-off between Copay and No-Copay?",
            expected_answer=(
                "Lower premium today versus higher claim participation later."
            ),
            failure_pattern="Customer only discusses premium.",
        ),
        advisor_checklist=[
            "Explain admissible claim.",
            "Explain Copay.",
            "Show financial simulation.",
            "Explain trade-offs.",
            "Verify understanding.",
            "Provide written summary.",
            "Document discussion.",
        ],
        advisor_confidence=AdvisorConfidence(
            ready_to_explain=True,
            ready_to_handle_objections=True,
            ready_to_compare_options=True,
            ready_to_document_recommendation=True,
        ),
        source_assets=[
            "knowledge_asset",
            "understanding_asset",
            "mental_model_asset",
            "financial_outcome_asset",
        ],
        certification=AdvisorIntelligenceCertification(
            status="PENDING",
            score=0,
        ),
    )