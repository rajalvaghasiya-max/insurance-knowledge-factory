from insurance_intelligence.concepts.waiting_periods.policy import (
    WaitingPeriodSemanticEffect,
    waiting_period_concept_policy,
)
from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    EvidenceReference,
    RelationshipType,
)
from insurance_intelligence.generic_knowledge.relevance_inventory import (
    SourceFragment,
    inventory_from_fragments,
)


def _fragment(fragment_id: str, text: str, *, source_class: str = "POLICY_WORDING") -> SourceFragment:
    applicability = ApplicabilityKey(product_reference="product://example")
    locator = f"page:{fragment_id}"
    return SourceFragment(
        fragment_id=fragment_id,
        text=text,
        locator=locator,
        source_class=source_class,
        applicability=applicability,
        evidence=EvidenceReference(
            evidence_id=f"evidence_{fragment_id}",
            source_document_id="doc_generic",
            source_document_version="v1",
            source_hash_sha256="a" * 64,
            locator=locator,
            authority_class=source_class,
        ),
    )


def _effects(result, fragment_id: str) -> set[str]:
    selection = next(
        item for item in result.selections if item.normative_unit.evidence.locator == f"page:{fragment_id}"
    )
    return set(selection.normative_unit.materially_affects)


def test_policy_is_generic_and_product_agnostic():
    policy = waiting_period_concept_policy()
    assert policy.concept == "waiting_periods"
    assert policy.policy_version == "waiting_period_policy_v1"
    serialized = repr(policy).casefold()
    assert "star_health" not in serialized
    assert "activ_one" not in serialized
    assert "aditya_birla" not in serialized


def test_policy_declares_all_initial_semantic_effects():
    policy = waiting_period_concept_policy()
    assert set(policy.semantic_effects) == set(WaitingPeriodSemanticEffect)


def test_policy_declares_governed_relationship_vocabulary():
    policy = waiting_period_concept_policy()
    assert RelationshipType.WAIVES in policy.allowed_relationship_types
    assert RelationshipType.MODIFIES in policy.allowed_relationship_types
    assert RelationshipType.APPLIES_WHEN in policy.allowed_relationship_types


def test_base_specific_disease_clause_is_high_recall_inventory():
    result = inventory_from_fragments(
        waiting_period_concept_policy().envelope,
        [_fragment("specific", "Specified disease / procedure Waiting Period (Code-Excl02) applies for 24 months and does not apply to claims arising due to accident.")],
    )
    effects = _effects(result, "specific")
    assert "DURATION" in effects
    assert "SCOPE" in effects
    assert "EXCEPTION" in effects


def test_continuity_and_portability_are_preserved():
    result = inventory_from_fragments(
        waiting_period_concept_policy().envelope,
        [_fragment("continuity", "If continuously covered without break under portability norms, the Waiting Period is reduced to the extent of prior coverage.")],
    )
    effects = _effects(result, "continuity")
    assert "CONTINUITY" in effects
    assert "PORTABILITY" in effects


def test_sum_insured_enhancement_is_preserved():
    result = inventory_from_fragments(
        waiting_period_concept_policy().envelope,
        [_fragment("si", "In case of enhancement of Sum Insured the exclusion shall apply afresh to the extent of Sum Insured increase.")],
    )
    effects = _effects(result, "si")
    assert "SUM_INSURED_ENHANCEMENT" in effects


def test_optional_reduction_is_not_treated_as_plain_duration_only():
    result = inventory_from_fragments(
        waiting_period_concept_policy().envelope,
        [_fragment("reduction", "Optional Cover: Reduction in Specific Disease Waiting Period from 2 years to 1 year.")],
    )
    effects = _effects(result, "reduction")
    assert "REDUCTION" in effects
    assert "OPTIONAL_COVER_INTERACTION" in effects
    assert "CROSS_CONCEPT_RELATIONSHIP" in effects


def test_benefit_scoped_waiver_is_relationship_material():
    result = inventory_from_fragments(
        waiting_period_concept_policy().envelope,
        [_fragment("waiver", "Under this chronic-care benefit, the Pre-Existing Disease Waiting Period and Initial Waiting Period will be waived for listed chronic conditions.")],
    )
    effects = _effects(result, "waiver")
    assert "WAIVER" in effects
    assert "BENEFIT_SCOPED_OVERRIDE" in effects
    assert "CROSS_CONCEPT_RELATIONSHIP" in effects


def test_renewal_and_new_member_effects_are_preserved():
    result = inventory_from_fragments(
        waiting_period_concept_policy().envelope,
        [_fragment("renewal", "Where a new member is added to this Policy on Renewal, all Waiting Periods will apply afresh for that member.")],
    )
    effects = _effects(result, "renewal")
    assert "RENEWAL_OR_REINSTATEMENT_EFFECT" in effects
    assert "APPLICABILITY" in effects


def test_schedule_delegated_duration_is_preserved_as_material():
    result = inventory_from_fragments(
        waiting_period_concept_policy().envelope,
        [_fragment("delegated", "Pre-Existing Disease expenses are excluded until expiry of years / months as specified in the Policy Schedule / Product Benefit Table.")],
    )
    effects = _effects(result, "delegated")
    assert "DURATION" in effects
    assert "APPLICABILITY" in effects
    assert "EFFECTIVE_DATE_OR_VERSION" in effects


def test_required_policy_wording_source_class_is_visible_when_missing():
    result = inventory_from_fragments(
        waiting_period_concept_policy().envelope,
        [_fragment("brochure", "Initial Waiting Period is 30 days.", source_class="BROCHURE")],
    )
    assert result.missing_required_source_classes == ("POLICY_WORDING",)
    assert not result.source_envelope_complete
