"""Education-first benefit assessment contracts for MO-026A.

These contracts sit above governed MO-025 benefit mechanics. They describe how a
single benefit/dimension may be assessed and explained without producing an
overall product score, ranking, winner, suitability conclusion, or recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BenefitAssessmentContractError(ValueError):
    """Raised when an MO-026A assessment contract violates an invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenefitAssessmentContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(
    values: tuple[str, ...],
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise BenefitAssessmentContractError(f"{field_name} must be a tuple")
    cleaned = tuple(_required_text(value, f"{field_name}[]") for value in values)
    if not allow_empty and not cleaned:
        raise BenefitAssessmentContractError(f"{field_name} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise BenefitAssessmentContractError(f"{field_name} must not contain duplicates")
    return cleaned


class AssessmentStatus(str, Enum):
    """Whether an assessment is usable on the governed evidence available."""

    ASSESSED = "ASSESSED"
    ASSESSED_WITH_LIMITATIONS = "ASSESSED_WITH_LIMITATIONS"
    NOT_SCORABLE = "NOT_SCORABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AssessmentBand(str, Enum):
    """Qualitative, non-cardinal description of one benefit/dimension."""

    VERY_STRONG = "VERY_STRONG"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    RESTRICTIVE = "RESTRICTIVE"
    VERY_RESTRICTIVE = "VERY_RESTRICTIVE"


class DecisionRole(str, Enum):
    """How a dimension should participate in education and later decision support."""

    PROTECTION_FLOOR = "PROTECTION_FLOOR"
    CORE_PROTECTION = "CORE_PROTECTION"
    PREFERENCE = "PREFERENCE"
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"
    PRICE = "PRICE"


class InteractionType(str, Enum):
    """Structural relationship between governed insurance dimensions."""

    MAY_REDUCE_EFFECT = "MAY_REDUCE_EFFECT"
    CONDITIONS_EFFECT = "CONDITIONS_EFFECT"
    LIMITS_SCOPE = "LIMITS_SCOPE"
    DEPENDS_ON = "DEPENDS_ON"
    SEQUENCES_WITH = "SEQUENCES_WITH"


class InteractionSeverity(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    MATERIAL = "MATERIAL"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class BenefitInteractionReference:
    """Evidence-preserving structural warning linking one dimension to another."""

    target_dimension_id: str
    interaction_type: InteractionType
    severity: InteractionSeverity
    explanation: str
    source_mechanic_ids: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_dimension_id",
            _required_text(self.target_dimension_id, "target_dimension_id"),
        )
        if not isinstance(self.interaction_type, InteractionType):
            raise BenefitAssessmentContractError("interaction_type must be an InteractionType")
        if not isinstance(self.severity, InteractionSeverity):
            raise BenefitAssessmentContractError("severity must be an InteractionSeverity")
        object.__setattr__(self, "explanation", _required_text(self.explanation, "explanation"))
        object.__setattr__(
            self,
            "source_mechanic_ids",
            _text_tuple(self.source_mechanic_ids, "source_mechanic_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "evidence_reference_ids",
            _text_tuple(
                self.evidence_reference_ids,
                "evidence_reference_ids",
                allow_empty=False,
            ),
        )


@dataclass(frozen=True)
class BenefitAssessment:
    """One governed, education-first assessment of a product benefit dimension."""

    assessment_id: str
    implementation_id: str
    concept_id: str
    dimension_id: str
    decision_role: DecisionRole
    status: AssessmentStatus
    assessment_band: AssessmentBand | None
    assessment_policy_id: str | None
    assessment_policy_version: str | None
    summary: str
    practical_meaning: str
    source_mechanic_ids: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    interaction_references: tuple[BenefitInteractionReference, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "assessment_id",
            "implementation_id",
            "concept_id",
            "dimension_id",
            "summary",
            "practical_meaning",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.decision_role, DecisionRole):
            raise BenefitAssessmentContractError("decision_role must be a DecisionRole")
        if not isinstance(self.status, AssessmentStatus):
            raise BenefitAssessmentContractError("status must be an AssessmentStatus")
        if self.assessment_band is not None and not isinstance(self.assessment_band, AssessmentBand):
            raise BenefitAssessmentContractError("assessment_band must be an AssessmentBand or None")
        object.__setattr__(
            self,
            "assessment_policy_id",
            _optional_text(self.assessment_policy_id, "assessment_policy_id"),
        )
        object.__setattr__(
            self,
            "assessment_policy_version",
            _optional_text(self.assessment_policy_version, "assessment_policy_version"),
        )
        object.__setattr__(
            self,
            "source_mechanic_ids",
            _text_tuple(self.source_mechanic_ids, "source_mechanic_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "evidence_reference_ids",
            _text_tuple(
                self.evidence_reference_ids,
                "evidence_reference_ids",
                allow_empty=False,
            ),
        )
        object.__setattr__(self, "limitations", _text_tuple(self.limitations, "limitations"))
        if not isinstance(self.interaction_references, tuple):
            raise BenefitAssessmentContractError("interaction_references must be a tuple")
        if not all(
            isinstance(item, BenefitInteractionReference) for item in self.interaction_references
        ):
            raise BenefitAssessmentContractError(
                "interaction_references must contain BenefitInteractionReference values"
            )

        if self.status in {
            AssessmentStatus.ASSESSED,
            AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        }:
            if self.assessment_band is None:
                raise BenefitAssessmentContractError(
                    "assessed statuses require an assessment_band"
                )
            if self.assessment_policy_id is None or self.assessment_policy_version is None:
                raise BenefitAssessmentContractError(
                    "assessed statuses require assessment policy identity and version"
                )
        else:
            if self.assessment_band is not None:
                raise BenefitAssessmentContractError(
                    "NOT_SCORABLE and NOT_APPLICABLE assessments cannot carry an assessment_band"
                )

        if self.status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS and not self.limitations:
            raise BenefitAssessmentContractError(
                "ASSESSED_WITH_LIMITATIONS requires at least one limitation"
            )
        if self.status is AssessmentStatus.NOT_SCORABLE and not self.limitations:
            raise BenefitAssessmentContractError(
                "NOT_SCORABLE requires a limitation explaining why assessment is unavailable"
            )

    @property
    def is_assessed(self) -> bool:
        return self.status in {
            AssessmentStatus.ASSESSED,
            AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        }

    @property
    def has_material_interaction(self) -> bool:
        return any(
            item.severity in {InteractionSeverity.MATERIAL, InteractionSeverity.CRITICAL}
            for item in self.interaction_references
        )

    @property
    def is_protection_floor(self) -> bool:
        return self.decision_role is DecisionRole.PROTECTION_FLOOR


__all__ = [
    "AssessmentBand",
    "AssessmentStatus",
    "BenefitAssessment",
    "BenefitAssessmentContractError",
    "BenefitInteractionReference",
    "DecisionRole",
    "InteractionSeverity",
    "InteractionType",
]
