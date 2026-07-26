from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CanonicalConcept:
    canonical_id: str
    display_name: str
    category: str
    aliases: tuple[str, ...]
    context_keywords: tuple[str, ...] = field(default_factory=tuple)
    semantic_type: str | None = None
    datatype: str | None = None
    allowed_units: tuple[str, ...] = field(default_factory=tuple)
    description: str | None = None


class CanonicalVocabulary:
    """
    Department IV seed vocabulary.

    This is intentionally small but extensible. Department IV must map insurer
    language to this vocabulary. Unknown or low-confidence terms go to review.
    """

    VERSION = "0.1"

    def __init__(self, concepts: list[CanonicalConcept] | None = None):
        self.concepts = concepts or self.seed_concepts()
        self._by_id = {concept.canonical_id: concept for concept in self.concepts}

    def get(self, canonical_id: str) -> CanonicalConcept | None:
        return self._by_id.get(canonical_id)

    def all(self) -> list[CanonicalConcept]:
        return list(self.concepts)

    def seed_concepts(self) -> list[CanonicalConcept]:
        c = CanonicalConcept
        return [
            c("PED_WAITING_PERIOD", "Pre-existing Disease Waiting Period", "waiting_period", ("pre-existing disease", "pre existing disease", "ped", "ped waiting period"), ("waiting period", "covered after", "months", "continuous coverage"), "waiting_period", "duration", ("days", "months", "years")),
            c("SPECIFIC_DISEASE_WAITING_PERIOD", "Specific Disease Waiting Period", "waiting_period", ("specific disease waiting period", "specified disease waiting period", "specified disease", "specific illness waiting"), ("excluded until", "continuous coverage", "listed conditions", "surgeries", "treatments"), "waiting_period", "duration", ("days", "months", "years")),
            c("INITIAL_WAITING_PERIOD", "Initial Waiting Period", "waiting_period", ("30-day waiting period", "initial waiting period", "thirty day waiting period"), ("first policy", "commencement date", "illness within", "accident"), "waiting_period", "duration", ("days", "months")),
            c("WAITING_PERIOD_REDUCTION", "Waiting Period Reduction", "optional_cover", ("jumpstart", "reduction in waiting period", "reduce waiting period", "waiting period waiver"), ("reduced", "30 days", "declared", "asthma", "diabetes", "hypertension"), "benefit_rule", "rule", ()),
            c("COPAY", "Co-payment", "cost_sharing", ("co-payment", "co payment", "copay", "co-pay", "cost sharing"), ("percentage", "admissible claims", "insured will bear", "does not reduce sum insured"), "cost_sharing", "percentage", ("percent", "%")),
            c("DEDUCTIBLE", "Deductible", "cost_sharing", ("deductible", "aggregate deductible", "per claim deductible"), ("not liable", "specified rupee", "before any benefits", "hospital cash"), "cost_sharing", "money", ("inr", "rupees", "days", "hours")),
            c("ROOM_RENT_LIMIT", "Room Rent Limit", "limit", ("room rent", "room charges", "room category", "room rent type", "shared room", "single private room"), ("boarding", "nursing", "hospital", "sub-limit", "eligible"), "coverage_limit", "money_or_category", ("inr", "percent", "category")),
            c("ICU_LIMIT", "ICU Limit", "limit", ("icu charges", "intensive care unit", "iccu", "intensive cardiac care"), ("critical care", "icu bed", "monitoring", "nursing"), "coverage_limit", "money_or_percent", ("inr", "percent")),
            c("PRE_HOSPITALIZATION", "Pre-hospitalization Expenses", "benefit", ("pre-hospitalization", "pre hospitalization", "pre-hospitalization expenses"), ("prior to", "immediately prior", "hospitalization", "medical expenses"), "coverage_benefit", "duration", ("days")),
            c("POST_HOSPITALIZATION", "Post-hospitalization Expenses", "benefit", ("post-hospitalization", "post hospitalization", "post-hospitalization expenses"), ("after discharge", "from date of discharge", "medical expenses"), "coverage_benefit", "duration", ("days")),
            c("AYUSH_COVERAGE", "AYUSH Coverage", "benefit", ("ayush", "ayush treatment", "ayurveda", "yoga", "naturopathy", "unani", "siddha", "homeopathy"), ("ayush hospital", "ayush day care", "inpatient"), "coverage_benefit", "boolean_or_limit", ()),
            c("DOMICILIARY_HOSPITALIZATION", "Domiciliary Hospitalization", "benefit", ("domiciliary hospitalization", "domiciliar hospitalization", "treatment at home"), ("home", "could not be removed", "non-availability of room", "consecutive days"), "coverage_benefit", "rule", ("days")),
            c("HOME_HEALTH_CARE", "Home Health Care", "benefit", ("home health care", "home treatment", "home healthcare"), ("pre-authorized", "network provider", "care plan", "treatment at home"), "coverage_benefit", "rule", ()),
            c("ORGAN_DONOR_EXPENSES", "Organ Donor Expenses", "benefit", ("organ donor", "organ donor expenses", "donated organ", "harvesting"), ("recipient", "transplantation", "human organs act"), "coverage_benefit", "rule", ()),
            c("RESTORATION_BENEFIT", "Restoration / Reload Benefit", "benefit", ("restore", "restoration", "reload", "super reload", "recharge", "reinstatement"), ("sum insured", "exhausted", "insufficient", "unlimited times", "policy year"), "coverage_benefit", "money_or_multiplier", ("inr", "times")),
            c("CUMULATIVE_BONUS", "Cumulative Bonus", "bonus", ("cumulative bonus", "no claim bonus", "ncb", "loyalty bonus", "super loyalty bonus", "power booster", "super credit"), ("each policy year", "sum insured", "renewed sum insured", "claim free", "increase"), "bonus", "percentage", ("percent", "%")),
            c("CLAIM_PROTECT", "Claim Protect / Non-medical Expense Waiver", "optional_cover", ("claim protect", "non-medical expense waiver", "non medical expense waiver", "non-medical expenses"), ("annexure i", "list i", "list ii", "list iii", "list iv", "waiver"), "optional_cover", "boolean", ()),
            c("MATERNITY_COVER", "Maternity Cover", "benefit", ("maternity", "maternity expenses", "childbirth", "delivery", "caesarean", "pregnancy"), ("lawful medical termination", "hospitalization", "miscarriage", "ectopic"), "coverage_benefit", "rule", ()),
            c("EXCLUSION", "Exclusion", "exclusion", ("exclusion", "excluded", "not covered", "permanent exclusion", "standard exclusions", "specific exclusions"), ("shall be excluded", "not admissible", "we shall not be liable"), "exclusion", "rule", ()),
            c("CLAIM_NOTIFICATION", "Claim Notification Requirement", "claim_requirement", ("notification of claim", "claim intimation", "intimate a claim", "notice of claim"), ("within 24 hours", "within 48 hours", "planned hospitalization", "emergency"), "claim_requirement", "duration", ("hours", "days")),
            c("CLAIM_DOCUMENTS", "Claim Documents Requirement", "claim_requirement", ("claim documents", "documents required", "documentation", "claim form", "discharge summary"), ("hospital bill", "diagnostic reports", "kyc", "neft", "fir"), "claim_requirement", "list", ()),
            c("GRACE_PERIOD", "Grace Period", "policy_administration", ("grace period",), ("premium", "renewal", "monthly", "thirty days", "fifteen days"), "policy_rule", "duration", ("days")),
            c("MORATORIUM_PERIOD", "Moratorium Period", "policy_administration", ("moratorium", "moratorium period"), ("sixty continuous months", "claim shall be contestable", "fraud"), "policy_rule", "duration", ("months", "years")),
            c("PORTABILITY", "Portability", "policy_administration", ("portability", "port the policy"), ("other insurers", "30 days before", "60 days", "continuity benefits"), "policy_rule", "rule", ()),
            c("MIGRATION", "Migration", "policy_administration", ("migration", "migrate the policy"), ("other health insurance products", "same company", "renewal date"), "policy_rule", "rule", ()),
        ]

    @staticmethod
    def normalize(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9%]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()
