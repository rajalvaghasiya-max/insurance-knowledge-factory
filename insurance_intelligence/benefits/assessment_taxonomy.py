"""Governed assessment dimension taxonomy for MO-026A.

The taxonomy defines what PolicyScna may assess and how each dimension participates
in education-first product analysis. It does not prescribe cross-dimension weights,
produce aggregate product scores, or make suitability recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.assessment_contracts import DecisionRole


class AssessmentTaxonomyError(ValueError):
    """Raised when a dimension definition or taxonomy is invalid."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessmentTaxonomyError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise AssessmentTaxonomyError(f"{field_name} must be a tuple")
    cleaned = tuple(_required_text(value, f"{field_name}[]") for value in values)
    if len(cleaned) != len(set(cleaned)):
        raise AssessmentTaxonomyError(f"{field_name} must not contain duplicates")
    return cleaned


class DimensionFamily(str, Enum):
    FINANCIAL_RESTRICTION = "FINANCIAL_RESTRICTION"
    WAITING_AND_ELIGIBILITY = "WAITING_AND_ELIGIBILITY"
    COVERAGE_CAPACITY = "COVERAGE_CAPACITY"
    COVERAGE_FEATURE = "COVERAGE_FEATURE"
    ACCESS_AND_USABILITY = "ACCESS_AND_USABILITY"
    LONG_TERM_POLICY = "LONG_TERM_POLICY"
    PRICE = "PRICE"


@dataclass(frozen=True)
class AssessmentDimensionDefinition:
    dimension_id: str
    canonical_name: str
    definition: str
    family: DimensionFamily
    decision_role: DecisionRole
    source_mechanic_ids: tuple[str, ...]
    assessment_policy_required: bool = True
    interaction_aware: bool = False
    non_suppressible_warning: bool = False

    def __post_init__(self) -> None:
        for field_name in ("dimension_id", "canonical_name", "definition"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.family, DimensionFamily):
            raise AssessmentTaxonomyError("family must be a DimensionFamily")
        if not isinstance(self.decision_role, DecisionRole):
            raise AssessmentTaxonomyError("decision_role must be a DecisionRole")
        object.__setattr__(
            self,
            "source_mechanic_ids",
            _text_tuple(self.source_mechanic_ids, "source_mechanic_ids"),
        )
        if not isinstance(self.assessment_policy_required, bool):
            raise AssessmentTaxonomyError("assessment_policy_required must be bool")
        if not isinstance(self.interaction_aware, bool):
            raise AssessmentTaxonomyError("interaction_aware must be bool")
        if not isinstance(self.non_suppressible_warning, bool):
            raise AssessmentTaxonomyError("non_suppressible_warning must be bool")
        if self.decision_role is DecisionRole.PROTECTION_FLOOR and not self.non_suppressible_warning:
            raise AssessmentTaxonomyError(
                "PROTECTION_FLOOR dimensions must enable non_suppressible_warning"
            )
        if self.decision_role is DecisionRole.PRICE and self.family is not DimensionFamily.PRICE:
            raise AssessmentTaxonomyError("PRICE decision role requires PRICE family")
        if self.family is DimensionFamily.PRICE and self.decision_role is not DecisionRole.PRICE:
            raise AssessmentTaxonomyError("PRICE family requires PRICE decision role")


COPAYMENT_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="copayment",
    canonical_name="Co-payment",
    definition=(
        "Customer cost-sharing obligation expressed with its percentage or amount, "
        "trigger, exceptions, and applicability scope."
    ),
    family=DimensionFamily.FINANCIAL_RESTRICTION,
    decision_role=DecisionRole.PROTECTION_FLOOR,
    source_mechanic_ids=(
        "copayment_percentage",
        "copayment_trigger",
        "copayment_exception",
        "copayment_scope",
    ),
    interaction_aware=True,
    non_suppressible_warning=True,
)

ROOM_RENT_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="room_rent_restriction",
    canonical_name="Room-rent restriction",
    definition=(
        "Room eligibility or monetary room-rent restriction together with any "
        "proportionate-deduction applicability and scope."
    ),
    family=DimensionFamily.FINANCIAL_RESTRICTION,
    decision_role=DecisionRole.PROTECTION_FLOOR,
    source_mechanic_ids=(
        "room_rent_limit",
        "room_category_eligibility",
        "proportionate_deduction",
        "proportionate_deduction_scope",
    ),
    interaction_aware=True,
    non_suppressible_warning=True,
)

DEDUCTIBLE_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="deductible",
    canonical_name="Deductible",
    definition="Amount or threshold the insured must bear before governed coverage responds.",
    family=DimensionFamily.FINANCIAL_RESTRICTION,
    decision_role=DecisionRole.PROTECTION_FLOOR,
    source_mechanic_ids=("deductible_amount", "deductible_type", "deductible_scope"),
    interaction_aware=True,
    non_suppressible_warning=True,
)

SUBLIMIT_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="procedure_or_disease_sublimit",
    canonical_name="Procedure or disease sub-limit",
    definition="A governed monetary or percentage cap that restricts payment for a covered treatment, disease, or procedure.",
    family=DimensionFamily.FINANCIAL_RESTRICTION,
    decision_role=DecisionRole.PROTECTION_FLOOR,
    source_mechanic_ids=("sublimit_value", "sublimit_scope", "sublimit_trigger"),
    interaction_aware=True,
    non_suppressible_warning=True,
)

PED_WAITING_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="ped_waiting_period",
    canonical_name="Pre-existing disease waiting period",
    definition="Waiting period that applies to governed pre-existing disease coverage.",
    family=DimensionFamily.WAITING_AND_ELIGIBILITY,
    decision_role=DecisionRole.CORE_PROTECTION,
    source_mechanic_ids=("ped_waiting_period",),
)

SPECIFIC_DISEASE_WAITING_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="specific_disease_waiting_period",
    canonical_name="Specific disease/procedure waiting period",
    definition="Waiting period applying to specified diseases, treatments, or procedures.",
    family=DimensionFamily.WAITING_AND_ELIGIBILITY,
    decision_role=DecisionRole.CORE_PROTECTION,
    source_mechanic_ids=("specific_disease_waiting_period", "specific_disease_waiting_scope"),
)

RESTORATION_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="restoration",
    canonical_name="Restoration / reload benefit",
    definition=(
        "Governed replenishment of available sum insured, including trigger, amount, "
        "frequency, same-claim use, and scope mechanics."
    ),
    family=DimensionFamily.COVERAGE_CAPACITY,
    decision_role=DecisionRole.CORE_PROTECTION,
    source_mechanic_ids=(
        "restoration_percentage",
        "restoration_count_per_policy_period",
        "trigger_requirement",
        "same_hospitalization_use",
        "subsequent_hospitalization_use",
        "first_claim_use",
        "covered_section_scope",
    ),
    interaction_aware=True,
)

CONSUMABLES_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="consumables_non_payables",
    canonical_name="Consumables / non-payable items coverage",
    definition="Coverage or exclusion treatment for governed consumable and non-payable hospitalization items.",
    family=DimensionFamily.COVERAGE_FEATURE,
    decision_role=DecisionRole.CORE_PROTECTION,
    source_mechanic_ids=("consumables_coverage", "non_payable_items_scope"),
)

HOME_HEALTHCARE_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="home_healthcare",
    canonical_name="Home healthcare",
    definition="Governed availability and scope of treatment delivered at home when covered by the product.",
    family=DimensionFamily.COVERAGE_FEATURE,
    decision_role=DecisionRole.CONTEXT_DEPENDENT,
    source_mechanic_ids=("home_healthcare_availability", "home_healthcare_scope"),
)

AYUSH_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="ayush",
    canonical_name="AYUSH coverage",
    definition="Governed coverage conditions for eligible AYUSH treatment.",
    family=DimensionFamily.COVERAGE_FEATURE,
    decision_role=DecisionRole.PREFERENCE,
    source_mechanic_ids=("ayush_coverage", "ayush_scope"),
)

NETWORK_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="network_access",
    canonical_name="Network / cashless access",
    definition="Governed or current access to network and cashless treatment subject to location and service availability.",
    family=DimensionFamily.ACCESS_AND_USABILITY,
    decision_role=DecisionRole.CONTEXT_DEPENDENT,
    source_mechanic_ids=("network_access", "cashless_access"),
)

PREMIUM_DIMENSION = AssessmentDimensionDefinition(
    dimension_id="quoted_premium",
    canonical_name="Quoted premium",
    definition="Customer-specific quoted price assessed only on a verified comparable quote basis.",
    family=DimensionFamily.PRICE,
    decision_role=DecisionRole.PRICE,
    source_mechanic_ids=("quote_final_premium",),
)

HEALTH_ASSESSMENT_DIMENSIONS: tuple[AssessmentDimensionDefinition, ...] = (
    AYUSH_DIMENSION,
    CONSUMABLES_DIMENSION,
    COPAYMENT_DIMENSION,
    DEDUCTIBLE_DIMENSION,
    HOME_HEALTHCARE_DIMENSION,
    NETWORK_DIMENSION,
    PED_WAITING_DIMENSION,
    PREMIUM_DIMENSION,
    RESTORATION_DIMENSION,
    ROOM_RENT_DIMENSION,
    SPECIFIC_DISEASE_WAITING_DIMENSION,
    SUBLIMIT_DIMENSION,
)


def registered_health_assessment_dimensions() -> tuple[AssessmentDimensionDefinition, ...]:
    """Return an immutable deterministic snapshot of the initial Health taxonomy."""

    ordered = tuple(sorted(HEALTH_ASSESSMENT_DIMENSIONS, key=lambda item: item.dimension_id))
    ids = tuple(item.dimension_id for item in ordered)
    if len(ids) != len(set(ids)):
        raise AssessmentTaxonomyError("health assessment taxonomy contains duplicate dimension ids")
    return ordered


__all__ = [
    "AssessmentDimensionDefinition",
    "AssessmentTaxonomyError",
    "AYUSH_DIMENSION",
    "CONSUMABLES_DIMENSION",
    "COPAYMENT_DIMENSION",
    "DEDUCTIBLE_DIMENSION",
    "DimensionFamily",
    "HEALTH_ASSESSMENT_DIMENSIONS",
    "HOME_HEALTHCARE_DIMENSION",
    "NETWORK_DIMENSION",
    "PED_WAITING_DIMENSION",
    "PREMIUM_DIMENSION",
    "RESTORATION_DIMENSION",
    "ROOM_RENT_DIMENSION",
    "SPECIFIC_DISEASE_WAITING_DIMENSION",
    "SUBLIMIT_DIMENSION",
    "registered_health_assessment_dimensions",
]
