from dataclasses import dataclass, field
from typing import List


@dataclass
class CustomerPsychology:
    visible_focus: str
    hidden_concern: str
    blind_spot: str
    confidence_level: str
    typical_assumption: str


@dataclass
class DecisionPsychology:
    biases: List[str]
    decision_pattern: str


@dataclass
class StorytellingAsset:
    title: str
    scenario: str
    outcome: str
    lesson: str


@dataclass
class VerificationQuestion:
    question: str
    expected_answer: str
    failure_pattern: str


@dataclass
class AdvisorConfidence:
    ready_to_explain: bool
    ready_to_handle_objections: bool
    ready_to_compare_options: bool
    ready_to_document_recommendation: bool


@dataclass
class AdvisorIntelligenceCertification:
    status: str
    score: int
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)


@dataclass
class AdvisorIntelligenceAsset:
    asset_id: str
    concept_id: str
    concept_name: str
    version: str

    customer_psychology: CustomerPsychology
    decision_psychology: DecisionPsychology
    common_objections: List[str]

    advisor_objective: str
    response_pattern: List[str]
    storytelling_asset: StorytellingAsset

    trust_builders: List[str]
    warning_signals: List[str]
    verification: VerificationQuestion
    advisor_checklist: List[str]
    advisor_confidence: AdvisorConfidence
    source_assets: List[str]

    certification: AdvisorIntelligenceCertification