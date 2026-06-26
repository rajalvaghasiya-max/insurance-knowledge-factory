from .decision_intelligence_models import (
    DecisionAssumption,
    DecisionContext,
    DecisionIntelligenceAsset,
    DecisionIntelligenceCertification,
    DecisionOption,
    DecisionReadiness,
    DecisionVerification,
    NextQuestion,
    TradeoffAnalysis,
)


def build_decision_intelligence_asset(
    concept_id: str,
) -> DecisionIntelligenceAsset:

    if concept_id != "copay":
        raise ValueError(
            f"Unsupported concept_id for DIA-001B: {concept_id}"
        )

    option_keep = DecisionOption(
        option_id="keep_copay",
        label="Keep Copay",
        benefit="Lower premium",
        cost="Higher out-of-pocket payment during claims",
        risk="Unexpected financial burden",
    )

    option_remove = DecisionOption(
        option_id="remove_copay",
        label="Remove Copay",
        benefit="Lower claim participation",
        cost="Higher premium",
        risk="Higher annual insurance cost",
    )

    return DecisionIntelligenceAsset(

        asset_id="",

        concept_id="copay",

        concept_name="Copay",

        version="1.0",

        decision_context=DecisionContext(

            topic="Copay",

            customer_goal="Select the most appropriate Copay option",

            decision_required="Choose between lower premium and lower claim participation",
        ),

        decision_options=[
            option_keep,
            option_remove,
        ],

        tradeoff_analysis=TradeoffAnalysis(

            primary_tradeoff="Lower premium today versus higher financial participation during future claims.",

            option_comparison=[
                option_keep,
                option_remove,
            ],
        ),

        assumptions=[

            DecisionAssumption(
                assumption="Customer has emergency savings.",
                impact_if_false="Unexpected claim expenses may create financial stress.",
            ),

            DecisionAssumption(
                assumption="Customer understands admissible claim calculation.",
                impact_if_false="Customer may underestimate Copay liability.",
            ),

            DecisionAssumption(
                assumption="Customer is comfortable paying a higher premium if needed.",
                impact_if_false="No-Copay option may not be affordable.",
            ),
        ],

        financial_implications={

            "lower_premium": "Benefit before claim",

            "higher_claim_payment": "Potential cost during hospitalization",
        },

        advisor_considerations=[

            "Verify customer understands admissible claim.",

            "Review financial simulation.",

            "Discuss trade-offs honestly.",

            "Confirm decision readiness.",
        ],

        decision_readiness=DecisionReadiness(

            understanding="COMPLETE",

            financial_awareness="COMPLETE",

            tradeoff_awareness="COMPLETE",

            overall="READY",
        ),

        recommended_next_questions=[

            NextQuestion(

                question="Could you comfortably pay ₹1 lakh unexpectedly?",

                reason="Assess claim-stage affordability.",
            ),

            NextQuestion(

                question="Would paying a higher premium reduce future financial stress?",

                reason="Evaluate risk preference.",
            ),
        ],

        warning_signals=[

            "Customer only focuses on premium.",

            "Customer cannot explain Copay.",

            "Customer ignores financial simulation.",
        ],

        verification=DecisionVerification(

            question="Why might someone choose No-Copay despite paying a higher premium?",

            expected_answer="To reduce future claim participation and improve financial certainty.",

            failure_pattern="Customer only compares premium amounts.",
        ),

        source_assets=[

            "knowledge_asset",

            "understanding_asset",

            "mental_model_asset",

            "financial_outcome_asset",

            "advisor_intelligence_asset",
        ],

        certification=DecisionIntelligenceCertification(

            status="PENDING",

            score=0,
        ),
    )