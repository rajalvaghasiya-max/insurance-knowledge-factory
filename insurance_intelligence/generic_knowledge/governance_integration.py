"""Governance and authority integration for MO-028B.G11.C5.

C5 keeps semantic publication, policy-instance resolution, and effective regulatory
interpretation orthogonal. It adapts the existing G2 authority resolver and G7 publication
eligibility decision instead of creating replacement engines.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.generic_knowledge.authority_resolution import (
    AuthorityResolution,
    ResolutionStatus as AuthorityResolutionStatus,
)
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    PublicationEligibilityDecision,
    PublicationEligibilityStatus,
)
from insurance_intelligence.generic_knowledge.resolution_status import ComputedResolution
from insurance_intelligence.generic_knowledge.waiting_period_schedule_resolution import InstanceDocumentClass


class GovernanceIntegrationError(ValueError):
    pass


class GovernanceLayer(str, Enum):
    SEMANTIC_PRODUCT = "SEMANTIC_PRODUCT"
    INSTANCE_VALUE = "INSTANCE_VALUE"
    REGULATORY_OVERLAY = "REGULATORY_OVERLAY"


class SemanticPublicationState(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    STALE = "STALE"


class RegulatoryInterpretationState(str, Enum):
    RESOLVED = "RESOLVED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    BLOCKED = "BLOCKED"


class RegulatoryEffectClass(str, Enum):
    REDUCE_ONLY = "REDUCE_ONLY"
    BENEFIT_ESTABLISHING = "BENEFIT_ESTABLISHING"
    MIXED_OR_UNKNOWN = "MIXED_OR_UNKNOWN"


class AnswerShape(str, Enum):
    SCALAR = "SCALAR"
    RANGE = "RANGE"
    CONDITIONAL = "CONDITIONAL"
    UNQUANTIFIED = "UNQUANTIFIED"


class AuthorityResolutionOutcome(str, Enum):
    NO_CONFLICT = "NO_CONFLICT"
    AUTHORITATIVE_OVERRIDE = "AUTHORITATIVE_OVERRIDE"
    UNRESOLVED_AUTHORITY_CONFLICT = "UNRESOLVED_AUTHORITY_CONFLICT"


@dataclass(frozen=True)
class DocumentAuthorityCapability:
    may_supply_semantics: bool
    may_supply_instance_values: bool
    requires_semantic_review: bool

    def __post_init__(self) -> None:
        for name in ("may_supply_semantics", "may_supply_instance_values", "requires_semantic_review"):
            if type(getattr(self, name)) is not bool:
                raise GovernanceIntegrationError(f"{name} must be boolean")


_DOCUMENT_CAPABILITIES = {
    InstanceDocumentClass.POLICY_WORDING: DocumentAuthorityCapability(True, False, True),
    InstanceDocumentClass.SCHEDULE: DocumentAuthorityCapability(False, True, False),
    InstanceDocumentClass.ENDORSEMENT: DocumentAuthorityCapability(True, True, True),
    InstanceDocumentClass.RIDER: DocumentAuthorityCapability(True, True, True),
    InstanceDocumentClass.CERTIFICATE: DocumentAuthorityCapability(False, False, False),
}


def document_authority_capability(document_class: InstanceDocumentClass) -> DocumentAuthorityCapability:
    if not isinstance(document_class, InstanceDocumentClass):
        raise GovernanceIntegrationError("document_class must be InstanceDocumentClass")
    return _DOCUMENT_CAPABILITIES[document_class]


@dataclass(frozen=True)
class EndorsementReleaseAssessment:
    document_class: InstanceDocumentClass
    semantic_review_approved: bool
    semantics_released: bool
    values_released: bool

    def __post_init__(self) -> None:
        if self.document_class not in (InstanceDocumentClass.ENDORSEMENT, InstanceDocumentClass.RIDER):
            raise GovernanceIntegrationError("release assessment requires endorsement or rider")
        if type(self.semantic_review_approved) is not bool:
            raise GovernanceIntegrationError("semantic_review_approved must be boolean")
        if self.semantics_released != self.semantic_review_approved:
            raise GovernanceIntegrationError("semantics release must follow semantic review")
        if self.values_released != self.semantic_review_approved:
            raise GovernanceIntegrationError("values release must follow semantic review")


def assess_endorsement_release(document_class: InstanceDocumentClass, *, semantic_review_approved: bool) -> EndorsementReleaseAssessment:
    if document_class not in (InstanceDocumentClass.ENDORSEMENT, InstanceDocumentClass.RIDER):
        raise GovernanceIntegrationError("only endorsements/riders use semantic release gate")
    if type(semantic_review_approved) is not bool:
        raise GovernanceIntegrationError("semantic_review_approved must be boolean")
    return EndorsementReleaseAssessment(
        document_class=document_class,
        semantic_review_approved=semantic_review_approved,
        semantics_released=semantic_review_approved,
        values_released=semantic_review_approved,
    )


@dataclass(frozen=True)
class SemanticPublicationAssessment:
    state: SemanticPublicationState
    answer_shape: AnswerShape
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    authority_decision_ids: tuple[str, ...] = ()
    review_requirement_ids: tuple[str, ...] = ()
    residue_ids: tuple[str, ...] = ()

    @property
    def publishable(self) -> bool:
        return self.state is SemanticPublicationState.ELIGIBLE


@dataclass(frozen=True)
class InstanceResolutionAssessment:
    layer: GovernanceLayer
    resolution: ComputedResolution
    policy_instance_reference: str
    resolution_cell_identity: object

    def __post_init__(self) -> None:
        if self.layer is not GovernanceLayer.INSTANCE_VALUE:
            raise GovernanceIntegrationError("instance assessment layer must be INSTANCE_VALUE")
        if not isinstance(self.resolution, ComputedResolution):
            raise GovernanceIntegrationError("resolution must be ComputedResolution")
        if not isinstance(self.policy_instance_reference, str) or not self.policy_instance_reference.strip():
            raise GovernanceIntegrationError("policy_instance_reference must be non-empty text")


@dataclass(frozen=True)
class RegulatoryInterpretationAssessment:
    layer: GovernanceLayer
    state: RegulatoryInterpretationState
    effect_class: RegulatoryEffectClass
    answer_shape: AnswerShape
    contract_fact_publishable: bool
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.layer is not GovernanceLayer.REGULATORY_OVERLAY:
            raise GovernanceIntegrationError("regulatory assessment layer must be REGULATORY_OVERLAY")
        if type(self.contract_fact_publishable) is not bool:
            raise GovernanceIntegrationError("contract_fact_publishable must be boolean")


def authority_outcome(resolution: AuthorityResolution, *, lower_authority_candidate_present: bool = False) -> AuthorityResolutionOutcome:
    if not isinstance(resolution, AuthorityResolution):
        raise GovernanceIntegrationError("resolution must be AuthorityResolution")
    if type(lower_authority_candidate_present) is not bool:
        raise GovernanceIntegrationError("lower_authority_candidate_present must be boolean")
    if resolution.status is AuthorityResolutionStatus.CONFLICTED:
        return AuthorityResolutionOutcome.UNRESOLVED_AUTHORITY_CONFLICT
    if resolution.status is AuthorityResolutionStatus.RESOLVED and lower_authority_candidate_present:
        return AuthorityResolutionOutcome.AUTHORITATIVE_OVERRIDE
    return AuthorityResolutionOutcome.NO_CONFLICT


def assess_regulatory_interpretation(*, verification_required: bool, effect_class: RegulatoryEffectClass) -> RegulatoryInterpretationAssessment:
    if type(verification_required) is not bool:
        raise GovernanceIntegrationError("verification_required must be boolean")
    if not isinstance(effect_class, RegulatoryEffectClass):
        raise GovernanceIntegrationError("effect_class must be RegulatoryEffectClass")
    if not verification_required:
        return RegulatoryInterpretationAssessment(
            GovernanceLayer.REGULATORY_OVERLAY,
            RegulatoryInterpretationState.RESOLVED,
            effect_class,
            AnswerShape.SCALAR,
            True,
        )
    if effect_class is RegulatoryEffectClass.REDUCE_ONLY:
        return RegulatoryInterpretationAssessment(
            GovernanceLayer.REGULATORY_OVERLAY,
            RegulatoryInterpretationState.VERIFICATION_REQUIRED,
            effect_class,
            AnswerShape.CONDITIONAL,
            True,
            ("effective interpretation requires regulatory verification",),
        )
    if effect_class is RegulatoryEffectClass.BENEFIT_ESTABLISHING:
        return RegulatoryInterpretationAssessment(
            GovernanceLayer.REGULATORY_OVERLAY,
            RegulatoryInterpretationState.VERIFICATION_REQUIRED,
            effect_class,
            AnswerShape.UNQUANTIFIED,
            False,
            ("affirmative benefit cannot publish until regulatory verification",),
        )
    return RegulatoryInterpretationAssessment(
        GovernanceLayer.REGULATORY_OVERLAY,
        RegulatoryInterpretationState.BLOCKED,
        effect_class,
        AnswerShape.UNQUANTIFIED,
        False,
        ("regulatory effect direction is mixed or unknown",),
    )


def assess_semantic_publication(
    decision: PublicationEligibilityDecision,
    *,
    answer_shape: AnswerShape,
    well_formed_instance_domain: bool = True,
    machine_semantic_conflict_detected: bool = False,
    legacy_recertification_required: bool = False,
    required_operand_governance_blocked: bool = False,
    regulatory_assessment: RegulatoryInterpretationAssessment | None = None,
) -> SemanticPublicationAssessment:
    """Enrich G7 publication without translating C1/C4 instance status into blockers."""
    if not isinstance(decision, PublicationEligibilityDecision):
        raise GovernanceIntegrationError("decision must be PublicationEligibilityDecision")
    if not isinstance(answer_shape, AnswerShape):
        raise GovernanceIntegrationError("answer_shape must be AnswerShape")
    for name, value in (
        ("well_formed_instance_domain", well_formed_instance_domain),
        ("machine_semantic_conflict_detected", machine_semantic_conflict_detected),
        ("legacy_recertification_required", legacy_recertification_required),
        ("required_operand_governance_blocked", required_operand_governance_blocked),
    ):
        if type(value) is not bool:
            raise GovernanceIntegrationError(f"{name} must be boolean")
    if regulatory_assessment is not None and not isinstance(regulatory_assessment, RegulatoryInterpretationAssessment):
        raise GovernanceIntegrationError("regulatory_assessment must be RegulatoryInterpretationAssessment")

    blockers = [blocker.code.value for blocker in decision.blockers]
    warnings: list[str] = []
    if not well_formed_instance_domain:
        blockers.append("NOT_YET_REPRESENTABLE")
    if legacy_recertification_required:
        blockers.append("LEGACY_RECERTIFICATION_REQUIRED")
    if required_operand_governance_blocked:
        blockers.append("OPERAND_GOVERNANCE_BLOCKED")
    if regulatory_assessment is not None:
        warnings.extend(regulatory_assessment.warnings)
        if not regulatory_assessment.contract_fact_publishable:
            blockers.append("UNSAFE_UNVERIFIED_REGULATORY_EFFECT")

    unique_blockers = tuple(sorted(set(blockers)))
    if unique_blockers or decision.status is PublicationEligibilityStatus.BLOCKED:
        state = SemanticPublicationState.STALE if "SOURCE_STALE" in unique_blockers else SemanticPublicationState.BLOCKED
        review_ids = ("candidate_semantic_conflict",) if machine_semantic_conflict_detected else ()
        return SemanticPublicationAssessment(
            state=state,
            answer_shape=answer_shape,
            blockers=unique_blockers,
            warnings=tuple(warnings),
            review_requirement_ids=review_ids,
        )

    if machine_semantic_conflict_detected:
        return SemanticPublicationAssessment(
            state=SemanticPublicationState.REVIEW_REQUIRED,
            answer_shape=answer_shape,
            warnings=tuple(warnings),
            review_requirement_ids=("candidate_semantic_conflict",),
        )

    return SemanticPublicationAssessment(
        state=SemanticPublicationState.ELIGIBLE,
        answer_shape=answer_shape,
        warnings=tuple(warnings),
    )


__all__ = [
    "AnswerShape",
    "AuthorityResolutionOutcome",
    "DocumentAuthorityCapability",
    "EndorsementReleaseAssessment",
    "GovernanceIntegrationError",
    "GovernanceLayer",
    "InstanceResolutionAssessment",
    "RegulatoryEffectClass",
    "RegulatoryInterpretationAssessment",
    "RegulatoryInterpretationState",
    "SemanticPublicationAssessment",
    "SemanticPublicationState",
    "assess_endorsement_release",
    "assess_regulatory_interpretation",
    "assess_semantic_publication",
    "authority_outcome",
    "document_authority_capability",
]
