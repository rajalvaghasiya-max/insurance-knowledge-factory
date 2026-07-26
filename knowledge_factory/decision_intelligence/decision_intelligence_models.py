from dataclasses import dataclass, field
from typing import List


@dataclass
class DecisionContext:
    topic: str
    customer_goal: str
    decision_required: str


@dataclass
class DecisionOption:
    option_id: str
    label: str
    benefit: str
    cost: str
    risk: str


@dataclass
class TradeoffAnalysis:
    primary_tradeoff: str
    option_comparison: List[DecisionOption]


@dataclass
class DecisionAssumption:
    assumption: str
    impact_if_false: str


@dataclass
class DecisionReadiness:
    understanding: str
    financial_awareness: str
    tradeoff_awareness: str
    overall: str


@dataclass
class NextQuestion:
    question: str
    reason: str


@dataclass
class DecisionVerification:
    question: str
    expected_answer: str
    failure_pattern: str


@dataclass
class DecisionIntelligenceCertification:
    status: str
    score: int
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)


@dataclass
class DecisionIntelligenceAsset:
    asset_id: str
    concept_id: str
    concept_name: str
    version: str

    decision_context: DecisionContext
    decision_options: List[DecisionOption]
    tradeoff_analysis: TradeoffAnalysis
    assumptions: List[DecisionAssumption]
    financial_implications: dict
    advisor_considerations: List[str]
    decision_readiness: DecisionReadiness
    recommended_next_questions: List[NextQuestion]
    warning_signals: List[str]
    verification: DecisionVerification
    source_assets: List[str]

    certification: DecisionIntelligenceCertification