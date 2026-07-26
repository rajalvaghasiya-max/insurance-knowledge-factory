"""
PolicyScna Department V — Learning Path Templates v1.0

Templates are deterministic curriculum recipes. They do not create content;
they only order existing Learning Primitives.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class LearningPathTemplate:
    path_type: str
    path_name: str
    learning_goal: str
    target_persona: str
    delivery_context: str
    estimated_duration_seconds: int
    difficulty: str
    primitive_sequence: List[str]
    optional_primitive_sequence: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    recommended_next_paths: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


STANDARD_LEARNING_PATH_TEMPLATES: List[LearningPathTemplate] = [
    LearningPathTemplate(
        path_type="quick_understanding",
        path_name="Quick Understanding",
        learning_goal="Understand the basic meaning of the concept quickly.",
        target_persona="consumer",
        delivery_context="quick_definition",
        estimated_duration_seconds=30,
        difficulty="basic",
        primitive_sequence=["definition", "purpose"],
        optional_primitive_sequence=["faq"],
        success_criteria=["Learner can explain the concept in one simple sentence."],
        recommended_next_paths=["claim_understanding", "buying_decision"],
        tags=["consumer", "quick", "basic"],
    ),
    LearningPathTemplate(
        path_type="claim_understanding",
        path_name="Claim Understanding",
        learning_goal="Understand how this concept affects a real claim outcome.",
        target_persona="consumer",
        delivery_context="claim_confusion",
        estimated_duration_seconds=150,
        difficulty="intermediate",
        primitive_sequence=["definition", "meaning", "money_flow", "worked_example", "misconception", "faq"],
        success_criteria=[
            "Learner can explain what happened during claim settlement.",
            "Learner can identify why their out-of-pocket amount may differ from the simple percentage.",
        ],
        recommended_next_paths=["deep_learning"],
        tags=["consumer", "claim", "calculation"],
    ),
    LearningPathTemplate(
        path_type="buying_decision",
        path_name="Buying Decision",
        learning_goal="Understand whether this feature may matter while comparing or buying a policy.",
        target_persona="consumer_or_advisor",
        delivery_context="comparison_or_purchase",
        estimated_duration_seconds=120,
        difficulty="intermediate",
        primitive_sequence=["definition", "purpose", "suitability", "related_concepts"],
        success_criteria=["Learner can state when this feature may or may not be suitable."],
        recommended_next_paths=["advisor_teaching", "deep_learning"],
        tags=["comparison", "recommendation", "purchase"],
    ),
    LearningPathTemplate(
        path_type="advisor_teaching",
        path_name="Advisor Teaching",
        learning_goal="Enable an advisor to explain the concept clearly to another person.",
        target_persona="advisor",
        delivery_context="advisor_training",
        estimated_duration_seconds=240,
        difficulty="advisor",
        primitive_sequence=["definition", "meaning", "money_flow", "worked_example", "misconception", "advisor_note"],
        optional_primitive_sequence=["source_example", "related_concepts"],
        success_criteria=["Advisor can teach the concept using a correct example and call out common misunderstanding."],
        recommended_next_paths=["deep_learning"],
        tags=["advisor", "training", "explanation"],
    ),
    LearningPathTemplate(
        path_type="deep_learning",
        path_name="Deep Learning",
        learning_goal="Build complete concept understanding using all available certified primitives.",
        target_persona="advisor_or_power_user",
        delivery_context="full_learning",
        estimated_duration_seconds=420,
        difficulty="advanced",
        primitive_sequence=[
            "definition",
            "meaning",
            "purpose",
            "money_flow",
            "worked_example",
            "misconception",
            "faq",
            "suitability",
            "related_concepts",
            "advisor_note",
            "source_example",
        ],
        success_criteria=["Learner can define, explain, calculate, compare, and teach the concept."],
        recommended_next_paths=[],
        tags=["advisor", "learning", "complete"],
    ),
]
