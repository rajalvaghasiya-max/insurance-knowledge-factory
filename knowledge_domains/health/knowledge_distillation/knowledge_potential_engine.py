from __future__ import annotations

from .distillation_models import KnowledgePotentialScore
from .observation_models import ObservationRecord


_IMPACT_SCORE = {
    "none": 0,
    "low": 3,
    "medium": 6,
    "high": 8,
    "very high": 10,
    "critical": 10,
    "unknown": 4,
}

_FREQUENCY_BONUS = {
    "rare": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "very high": 4,
    "unknown": 1,
}


def impact_score(value: str) -> int:
    return _IMPACT_SCORE.get(value.strip().lower(), 4)


class KnowledgePotentialEngine:
    """Scores how much institutional intelligence an observation can manufacture."""

    def score(self, observation: ObservationRecord) -> KnowledgePotentialScore:
        text = f"{observation.title} {observation.observation}".lower()
        freq_bonus = _FREQUENCY_BONUS.get(observation.frequency.strip().lower(), 1)

        financial = min(10, impact_score(observation.financial_impact) + (2 if any(k in text for k in ["bill", "premium", "cash", "amount", "lakh"]) else 0))
        emotional = min(10, impact_score(observation.emotional_impact) + (2 if any(k in text for k in ["shock", "anger", "fear", "regret", "panic"]) else 0))
        decision = min(10, impact_score(observation.decision_impact) + (2 if any(k in text for k in ["choose", "buy", "select", "decision"]) else 0))
        teaching = min(10, 5 + freq_bonus + (2 if any(k in text for k in ["misunderstand", "think", "assume", "example", "explain"]) else 0))
        behaviour = min(10, 4 + freq_bonus + (2 if any(k in text for k in ["buy", "ignore", "regret", "calculate", "ask"]) else 0))
        relationship = min(10, len(set(observation.linked_concepts)) + 3)

        return KnowledgePotentialScore(
            financial=financial,
            teaching=teaching,
            behaviour=behaviour,
            decision=decision,
            relationship=relationship,
            emotional=emotional,
        )
