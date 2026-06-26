from __future__ import annotations

from typing import Any, Dict

from .observation_models import ObservationRecord


class ObservationClassifier:
    """Deterministic classifier for observation records."""

    KEYWORDS = {
        "misconception": ["think", "assume", "believe", "misunderstand", "illusion", "fallacy", "myth"],
        "financial": ["bill", "premium", "cash", "amount", "lakhs", "out-of-pocket", "savings", "liability"],
        "claim": ["claim", "tpa", "cashless", "discharge", "hospital", "reimbursement"],
        "advisor": ["advisor", "agent", "relationship manager", "sales", "explain"],
        "decision": ["choose", "buy", "select", "decision", "trade-off", "compare"],
        "teaching": ["example", "analogy", "script", "golden rule", "explanation"],
    }

    def classify(self, observation: ObservationRecord) -> Dict[str, Any]:
        text = f"{observation.title} {observation.observation}".lower()
        detected = []
        for label, keywords in self.KEYWORDS.items():
            if any(k in text for k in keywords):
                detected.append(label)

        primary = observation.observation_type if observation.observation_type != "unknown" else (detected[0] if detected else "general")
        return {
            "primary_category": observation.category,
            "primary_type": primary,
            "detected_signals": sorted(set(detected)),
            "needs_human_review": observation.confidence.lower() in {"low", "unknown"},
        }
