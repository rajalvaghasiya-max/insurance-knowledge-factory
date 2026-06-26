from __future__ import annotations

from typing import Dict, List, Set

from .observation_models import ObservationRecord


class RelationshipDetector:
    """Detects related concepts using deterministic keyword rules."""

    RELATIONSHIP_KEYWORDS: Dict[str, List[str]] = {
        "admissible_claim": ["approved", "admissible", "allowed", "net approved"],
        "claim_settlement": ["claim", "settlement", "payout", "approval"],
        "non_medical_expenses": ["non-medical", "consumables", "gloves", "masks", "syringes"],
        "room_rent_limit": ["room rent", "room", "deluxe", "cap"],
        "deductible": ["deductible", "threshold"],
        "zone_copay": ["zone", "metro", "mumbai", "delhi", "tier"],
        "cashless": ["cashless", "tpa", "pre-authorization", "discharge"],
        "premium": ["premium", "discount", "cheap", "savings"],
        "no_claim_bonus": ["ncb", "no-claim", "bonus"],
        "restoration": ["restore", "restoration", "refill"],
        "waiting_period": ["waiting period", "continuity", "portability"],
    }

    def detect(self, observation: ObservationRecord) -> List[str]:
        text = f"{observation.title} {observation.observation}".lower()
        relationships: Set[str] = set(observation.linked_concepts)
        relationships.add(observation.concept_id)
        for concept, keywords in self.RELATIONSHIP_KEYWORDS.items():
            if any(k in text for k in keywords):
                relationships.add(concept)
        return sorted(relationships)
