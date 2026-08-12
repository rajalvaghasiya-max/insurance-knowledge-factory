from __future__ import annotations

from datetime import date

import pytest

from insurance_intelligence.contracts.terminology import (
    CanonicalConceptFamily,
    EvidenceSpan,
    TerminologyPublicationStatus,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
)
from insurance_intelligence.terminology.governed_concept_aliases import (
    BenefitConceptIdentityStatus,
    GovernedBenefitConceptResolver,
    GovernedConceptAlias,
    GovernedConceptAliasError,
    GovernedConceptAliasRegistry,
    comparison_identity_compatible,
)
from insurance_intelligence.terminology.mo028c_benefit_seed import (
    MO028C_GOVERNED_BENEFIT_ALIASES,
    build_mo028c_governed_alias_registry,
)


AS_OF = date(2026, 8, 12)


def _concept(concept_id: str, name: str, *, ambiguity_group: str | None = None) -> CanonicalConceptDefinition:
    return CanonicalConceptDefinition(
        concept=CanonicalConceptFamily(
            concept_family_id=concept_id,
            canonical_name=name,
            definition=f"Governed test concept for {name}.",
            domain="health",
            concept_subtype="benefit",
        ),
        concept_type="BENEFIT",
        ambiguity_group=ambiguity_group,
    )


def _alias(
    alias_id: str,
    alias_text: str,
    concept_id: str,
    *,
    review_status: TerminologyReviewStatus = TerminologyReviewStatus.PUBLISHED,
    publication_status: TerminologyPublicationStatus = TerminologyPublicationStatus.AUTHORITATIVE,
    governance_version: str = "g1-test-v1",
) -> GovernedConceptAlias:
    return GovernedConceptAlias(
        alias_id=alias_id,
        alias_text=alias_text,
        concept_id=concept_id,
        evidence_spans=(
            EvidenceSpan(
                source_id="g1-test-source",
                document_id="g1-test-document",
                locator=alias_id,
                quoted_text=alias_text,
                evidence_id=f"evidence:{alias_id}",
            ),
        ),
        review_decision_id=f"review:{alias_id}",
        governance_version=governance_version,
        review_status=review_status,
        publication_status=publication_status,
    )


def test_seed_exact_alias_resolves_with_governance_and_provenance() -> None:
    resolver = GovernedBenefitConceptResolver(build_mo028c_governed_alias_registry())
    result = resolver.resolve("Cataract", as_of=AS_OF)
    assert result.status is BenefitConceptIdentityStatus.RESOLVED
    assert result.concept_id == "health:benefit:cataract"
    assert result.raw_label == "Cataract"
    assert result.normalised_label == "cataract"
    assert result.matched_alias_ids == ("mo028c_alias_cataract",)
    assert result.matched_review_decision_ids == ("MO_028C_G0_SOURCE_PRESSURE_CERTIFICATION",)
    assert result.alias_registry_version == "mo028c_benefit_alias_registry_v1"
    assert result.alias_registry_snapshot_id.startswith("gcar_")


def test_case_and_punctuation_normalisation_remain_deterministic() -> None:
    resolver = GovernedBenefitConceptResolver(build_mo028c_governed_alias_registry())
    assert resolver.resolve("  road-ambulance ", as_of=AS_OF).status is BenefitConceptIdentityStatus.RESOLVED
    assert resolver.resolve("  ROAD AMBULANCE ", as_of=AS_OF).concept_id == "health:benefit:road_ambulance"


def test_unknown_label_is_not_found_and_never_best_guessed() -> None:
    resolver = GovernedBenefitConceptResolver(build_mo028c_governed_alias_registry())
    result = resolver.resolve("Premium Cataract Lens Upgrade", as_of=AS_OF)
    assert result.status is BenefitConceptIdentityStatus.NOT_FOUND
    assert result.selected_concept is None
    assert result.candidates == ()
    assert result.matched_alias_ids == ()


def test_unreviewed_or_unpublished_alias_does_not_resolve_authoritatively() -> None:
    concepts = CanonicalConceptRegistry((_concept("health:benefit:test", "Test Benefit"),))
    registry = GovernedConceptAliasRegistry(
        concept_registry=concepts,
        aliases=(
            _alias(
                "candidate",
                "Candidate Benefit",
                "health:benefit:test",
                review_status=TerminologyReviewStatus.REVIEW_REQUIRED,
                publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
            ),
        ),
        registry_version="candidate-v1",
    )
    result = GovernedBenefitConceptResolver(registry).resolve("Candidate Benefit", as_of=AS_OF)
    assert result.status is BenefitConceptIdentityStatus.NOT_FOUND


def test_shared_broad_label_requires_explicit_ambiguity_group_and_returns_ambiguous() -> None:
    concepts = CanonicalConceptRegistry(
        (
            _concept("health:benefit:road_ambulance", "Road Ambulance", ambiguity_group="ambulance"),
            _concept("health:benefit:air_ambulance", "Air Ambulance", ambiguity_group="ambulance"),
        )
    )
    registry = GovernedConceptAliasRegistry(
        concept_registry=concepts,
        aliases=(
            _alias("ambulance-road", "Ambulance", "health:benefit:road_ambulance"),
            _alias("ambulance-air", "Ambulance", "health:benefit:air_ambulance"),
        ),
        registry_version="ambulance-v1",
    )
    result = GovernedBenefitConceptResolver(registry).resolve("Ambulance", as_of=AS_OF)
    assert result.status is BenefitConceptIdentityStatus.AMBIGUOUS
    assert result.selected_concept is None
    assert {item.concept_id for item in result.candidates} == {
        "health:benefit:road_ambulance",
        "health:benefit:air_ambulance",
    }


def test_shared_alias_without_explicit_ambiguity_group_is_registry_conflict() -> None:
    concepts = CanonicalConceptRegistry(
        (
            _concept("health:benefit:a", "Benefit A"),
            _concept("health:benefit:b", "Benefit B"),
        )
    )
    with pytest.raises(GovernedConceptAliasError, match="ambiguity_group"):
        GovernedConceptAliasRegistry(
            concept_registry=concepts,
            aliases=(
                _alias("a", "Shared", "health:benefit:a"),
                _alias("b", "Shared", "health:benefit:b"),
            ),
            registry_version="invalid-v1",
        )


def test_alias_requires_evidence_review_decision_and_governance_version() -> None:
    with pytest.raises(GovernedConceptAliasError):
        GovernedConceptAlias(
            alias_id="bad",
            alias_text="Bad Alias",
            concept_id="health:benefit:test",
            evidence_spans=(),
            review_decision_id="review",
            governance_version="v1",
            review_status=TerminologyReviewStatus.PUBLISHED,
            publication_status=TerminologyPublicationStatus.AUTHORITATIVE,
        )


def test_bare_existing_concept_language_is_not_automatically_comparison_authoritative() -> None:
    concept = CanonicalConceptDefinition(
        concept=CanonicalConceptFamily(
            concept_family_id="health:benefit:bare",
            canonical_name="Bare Benefit",
            definition="Bare terminology concept.",
            domain="health",
        ),
        concept_type="BENEFIT",
        aliases=("Bare Alias",),
    )
    resolver = GovernedBenefitConceptResolver(
        GovernedConceptAliasRegistry(
            concept_registry=CanonicalConceptRegistry((concept,)),
            aliases=(),
            registry_version="bare-v1",
        )
    )
    assert resolver.resolve("Bare Alias", as_of=AS_OF).status is BenefitConceptIdentityStatus.NOT_FOUND


def test_comparison_identity_requires_same_concept_and_same_governed_alias_snapshot() -> None:
    registry = build_mo028c_governed_alias_registry()
    resolver = GovernedBenefitConceptResolver(registry)
    left = resolver.resolve("Cataract", as_of=AS_OF)
    right = resolver.resolve("Cataract", as_of=AS_OF)
    assert comparison_identity_compatible(left, right) is True

    changed = GovernedConceptAliasRegistry(
        concept_registry=registry.concept_registry,
        aliases=MO028C_GOVERNED_BENEFIT_ALIASES,
        registry_version="mo028c_benefit_alias_registry_v2",
    )
    changed_result = GovernedBenefitConceptResolver(changed).resolve("Cataract", as_of=AS_OF)
    assert changed_result.concept_id == left.concept_id
    assert comparison_identity_compatible(left, changed_result) is False


def test_invalid_input_never_publishes_identity() -> None:
    resolver = GovernedBenefitConceptResolver(build_mo028c_governed_alias_registry())
    result = resolver.resolve(None, as_of=AS_OF)
    assert result.status is BenefitConceptIdentityStatus.INVALID_INPUT
    assert result.selected_concept is None
    assert result.concept_id is None
