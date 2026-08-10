from dataclasses import replace

import pytest

from insurance_intelligence.coverage_registry.health_generalized_current import (
    WAITING_PERIOD_PUBLICATIONS,
)
from insurance_intelligence.generic_knowledge.assessment_policy import (
    AssessmentPolicy,
    AssessmentPolicyError,
    AssessmentPolicyRegistry,
)
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    dependency_binding_matches,
)
from insurance_intelligence.generic_knowledge.semantic_core import (
    ApplicabilitySchemaVersion,
    CanonicalConceptIdentity,
    HEALTH_APPLICABILITY_SCHEMA,
    HEALTH_ONTOLOGY_RELEASE,
    HEALTH_WAITING_PERIODS,
    InsuranceCategory,
    SemanticCoreError,
)


def test_waiting_period_has_immutable_namespaced_canonical_identity():
    assert HEALTH_WAITING_PERIODS.canonical_id == "health.waiting_periods.base"
    assert HEALTH_WAITING_PERIODS.category is InsuranceCategory.HEALTH
    assert HEALTH_WAITING_PERIODS.fact_schema_id == "waiting_periods_v1"
    assert HEALTH_WAITING_PERIODS.concept_semantic_version == "1"


def test_canonical_identity_namespace_must_match_category():
    with pytest.raises(SemanticCoreError):
        CanonicalConceptIdentity(
            canonical_id="motor.waiting_periods.base",
            category=InsuranceCategory.HEALTH,
            concept_semantic_version="1",
            fact_schema_id="waiting_periods_v1",
        )


def test_canonical_identity_rejects_non_semantic_identifier_shape():
    with pytest.raises(SemanticCoreError):
        CanonicalConceptIdentity(
            canonical_id="Health Waiting Period",
            category=InsuranceCategory.HEALTH,
            concept_semantic_version="1",
            fact_schema_id="waiting_periods_v1",
        )


def test_health_ontology_and_applicability_versions_are_explicit():
    assert HEALTH_ONTOLOGY_RELEASE.release_id == "health_ontology_2026_08"
    assert HEALTH_APPLICABILITY_SCHEMA.version_id == "health_applicability_v1"
    assert "product_reference" in HEALTH_APPLICABILITY_SCHEMA.common_axes
    assert "policy_version" in HEALTH_APPLICABILITY_SCHEMA.common_axes


def test_applicability_schema_rejects_duplicate_axes():
    with pytest.raises(SemanticCoreError):
        ApplicabilitySchemaVersion(
            version_id="health_applicability_bad",
            common_axes=("zone", "zone"),
        )


def test_all_current_waiting_period_publications_bind_semantic_backbone_versions():
    assert WAITING_PERIOD_PUBLICATIONS
    for publication in WAITING_PERIOD_PUBLICATIONS.values():
        binding = publication.dependency_binding
        assert binding.ontology_release == HEALTH_ONTOLOGY_RELEASE.release_id
        assert binding.canonical_concept_id == HEALTH_WAITING_PERIODS.canonical_id
        assert binding.concept_semantic_version == HEALTH_WAITING_PERIODS.concept_semantic_version
        assert binding.applicability_schema_version == HEALTH_APPLICABILITY_SCHEMA.version_id
        assert binding.mapping_policy_version == "waiting_period_mapping_v1"


def test_applicability_schema_change_invalidates_old_dependency_binding():
    publication = next(iter(WAITING_PERIOD_PUBLICATIONS.values()))
    published = publication.dependency_binding
    current = replace(
        published,
        applicability_schema_version="health_applicability_v2",
    )
    assert dependency_binding_matches(published, current) is False


def test_ontology_release_change_invalidates_old_dependency_binding():
    publication = next(iter(WAITING_PERIOD_PUBLICATIONS.values()))
    published = publication.dependency_binding
    current = replace(published, ontology_release="health_ontology_2026_09")
    assert dependency_binding_matches(published, current) is False


def test_concept_semantic_version_change_invalidates_old_dependency_binding():
    publication = next(iter(WAITING_PERIOD_PUBLICATIONS.values()))
    published = publication.dependency_binding
    current = replace(published, concept_semantic_version="2")
    assert dependency_binding_matches(published, current) is False


def test_assessment_policy_is_keyed_on_canonical_id_and_separate_from_personalization():
    policy = AssessmentPolicy(
        policy_id="assessment:health:copayment:v1",
        version="1",
        canonical_concept_id="health.copayment.base",
        mandatory_consideration=True,
        suppression_allowed=False,
        warning_required=True,
        rationale="Copayment materially changes realized admissibility and must be surfaced.",
    )
    registry = AssessmentPolicyRegistry((policy,))
    assert registry.for_concept("health.copayment.base") == policy
    assert registry.must_surface("health.copayment.base") is True
    assert not hasattr(policy, "customer_age")
    assert not hasattr(policy, "customer_priority")
    assert not hasattr(policy, "recommendation")


def test_mandatory_assessment_concept_cannot_allow_suppression():
    with pytest.raises(AssessmentPolicyError):
        AssessmentPolicy(
            policy_id="assessment:health:copayment:bad",
            version="1",
            canonical_concept_id="health.copayment.base",
            mandatory_consideration=True,
            suppression_allowed=True,
        )


def test_assessment_policy_registry_allows_one_active_policy_per_concept():
    first = AssessmentPolicy(
        policy_id="assessment:health:copayment:v1",
        version="1",
        canonical_concept_id="health.copayment.base",
        mandatory_consideration=True,
        suppression_allowed=False,
    )
    second = AssessmentPolicy(
        policy_id="assessment:health:copayment:v2",
        version="2",
        canonical_concept_id="health.copayment.base",
        mandatory_consideration=True,
        suppression_allowed=False,
    )
    with pytest.raises(AssessmentPolicyError):
        AssessmentPolicyRegistry((first, second))
