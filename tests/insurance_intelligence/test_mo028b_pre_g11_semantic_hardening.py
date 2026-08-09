from dataclasses import replace

import pytest

from insurance_intelligence.generic_knowledge.assessment_policy import (
    AssessmentPolicy,
    AssessmentPolicyError,
    AssessmentPolicyRegistry,
)
from insurance_intelligence.generic_knowledge.health_semantic_baseline import (
    HEALTH_ASSESSMENT_POLICIES,
    HEALTH_CANONICAL_CONCEPTS,
    HEALTH_ONTOLOGY_RELEASE,
)
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    PublicationDependencyBinding,
)
from insurance_intelligence.generic_knowledge.semantic_dependencies import (
    SemanticPublicationDependencyBinding,
    semantic_dependency_matches,
)
from insurance_intelligence.generic_knowledge.semantic_registry import (
    ApplicabilitySchema,
    CanonicalConcept,
    CanonicalConceptRegistry,
    InsuranceCategory,
    SemanticRegistryError,
)


def _base_binding():
    return PublicationDependencyBinding(
        ontology_version="waiting_periods_v1",
        source_document_id="doc",
        source_document_version="v1",
        source_hash_sha256="abc123",
        review_decision_version="review-v1",
    )


def _semantic_binding():
    return SemanticPublicationDependencyBinding(
        base=_base_binding(),
        ontology_release=HEALTH_ONTOLOGY_RELEASE,
        canonical_concept_id="health.waiting_periods",
        concept_version="1",
        applicability_schema_version="1",
        mapping_policy_version="waiting-period-mapping-v1",
    )


def test_health_baseline_has_immutable_category_namespaced_ids():
    ids = {item.canonical_id for item in HEALTH_CANONICAL_CONCEPTS.concepts}
    assert ids == {
        "health.waiting_periods",
        "health.copayment",
        "health.room_rent_restriction",
        "health.restoration",
    }
    assert all(item.ontology_release == HEALTH_ONTOLOGY_RELEASE for item in HEALTH_CANONICAL_CONCEPTS.concepts)


def test_legacy_waiting_period_term_resolves_to_canonical_health_id():
    concept = HEALTH_CANONICAL_CONCEPTS.resolve_term(
        "waiting_periods", category=InsuranceCategory.HEALTH
    )
    assert concept.canonical_id == "health.waiting_periods"
    assert concept.fact_schema_id == "waiting_periods_v1"


def test_resolution_is_category_scoped_and_fails_closed():
    with pytest.raises(SemanticRegistryError, match="unresolved"):
        HEALTH_CANONICAL_CONCEPTS.resolve_term(
            "waiting_periods", category=InsuranceCategory.MOTOR
        )


def test_ambiguous_alias_resolution_fails_closed():
    applicability = ApplicabilitySchema(schema_id="health.test", version="1")
    registry = CanonicalConceptRegistry(
        (
            CanonicalConcept(
                canonical_id="health.a",
                category=InsuranceCategory.HEALTH,
                concept_version="1",
                ontology_release="r1",
                fact_schema_id="a",
                applicability_schema=applicability,
                definition_reference_id="def:a",
                gloss="A",
                aliases=("same",),
            ),
            CanonicalConcept(
                canonical_id="health.b",
                category=InsuranceCategory.HEALTH,
                concept_version="1",
                ontology_release="r1",
                fact_schema_id="b",
                applicability_schema=applicability,
                definition_reference_id="def:b",
                gloss="B",
                aliases=("same",),
            ),
        )
    )
    with pytest.raises(SemanticRegistryError, match="ambiguous"):
        registry.resolve_term("same", category=InsuranceCategory.HEALTH)


def test_restoration_does_not_resolve_recharge_as_a_synonym():
    with pytest.raises(SemanticRegistryError):
        HEALTH_CANONICAL_CONCEPTS.resolve_term(
            "recharge", category=InsuranceCategory.HEALTH
        )


def test_applicability_schema_supports_governed_extension_axes():
    base = ApplicabilitySchema(
        schema_id="health.waiting_periods.applicability",
        version="1",
        common_axes=("variant", "sum_insured_band"),
    )
    extended = ApplicabilitySchema(
        schema_id=base.schema_id,
        version="2",
        common_axes=base.common_axes,
        extension_axes=("network_tier",),
    )
    assert base.axes == ("variant", "sum_insured_band")
    assert extended.axes == ("variant", "sum_insured_band", "network_tier")
    assert extended.version != base.version


def test_applicability_axes_cannot_overlap():
    with pytest.raises(SemanticRegistryError, match="must not overlap"):
        ApplicabilitySchema(
            schema_id="x",
            version="1",
            common_axes=("zone",),
            extension_axes=("zone",),
        )


def test_assessment_policy_is_separate_from_canonical_concept():
    copay = HEALTH_CANONICAL_CONCEPTS.get("health.copayment")
    policy = HEALTH_ASSESSMENT_POLICIES.for_concept("health.copayment")
    assert copay is not None
    assert policy is not None
    assert not hasattr(copay, "mandatory_consideration")
    assert policy.mandatory_consideration is True
    assert policy.suppression_allowed is False


def test_assessment_policy_makes_copay_and_room_rent_mandatory_to_surface():
    assert HEALTH_ASSESSMENT_POLICIES.must_surface("health.copayment")
    assert HEALTH_ASSESSMENT_POLICIES.must_surface("health.room_rent_restriction")
    assert not HEALTH_ASSESSMENT_POLICIES.must_surface("health.restoration")


def test_mandatory_consideration_cannot_allow_suppression():
    with pytest.raises(AssessmentPolicyError, match="cannot allow suppression"):
        AssessmentPolicy(
            policy_id="p",
            version="1",
            canonical_concept_id="health.test",
            mandatory_consideration=True,
            suppression_allowed=True,
        )


def test_assessment_policy_registry_allows_only_one_active_policy_per_concept():
    first = AssessmentPolicy(
        policy_id="p1",
        version="1",
        canonical_concept_id="health.test",
        mandatory_consideration=False,
        suppression_allowed=True,
    )
    second = AssessmentPolicy(
        policy_id="p2",
        version="2",
        canonical_concept_id="health.test",
        mandatory_consideration=False,
        suppression_allowed=True,
    )
    with pytest.raises(AssessmentPolicyError, match="only one active"):
        AssessmentPolicyRegistry((first, second))


def test_semantic_dependency_wraps_existing_g7_binding_without_replacing_it():
    binding = _semantic_binding()
    assert binding.base.ontology_version == "waiting_periods_v1"
    assert binding.canonical_concept_id == "health.waiting_periods"
    assert binding.ontology_release == HEALTH_ONTOLOGY_RELEASE


def test_semantic_dependency_exact_match_is_reusable():
    binding = _semantic_binding()
    assert semantic_dependency_matches(binding, binding)


def test_new_applicability_schema_version_invalidates_semantic_dependency():
    published = _semantic_binding()
    current = replace(published, applicability_schema_version="2")
    assert not semantic_dependency_matches(published, current)


def test_new_concept_version_invalidates_semantic_dependency():
    published = _semantic_binding()
    current = replace(published, concept_version="2")
    assert not semantic_dependency_matches(published, current)


def test_new_mapping_policy_invalidates_semantic_dependency():
    published = _semantic_binding()
    current = replace(published, mapping_policy_version="waiting-period-mapping-v2")
    assert not semantic_dependency_matches(published, current)


def test_new_assessment_policy_version_can_be_dependency_bound_when_required():
    published = replace(_semantic_binding(), assessment_policy_version="assessment-v1")
    current = replace(published, assessment_policy_version="assessment-v2")
    assert not semantic_dependency_matches(published, current)
