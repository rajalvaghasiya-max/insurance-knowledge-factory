import pytest

from insurance_intelligence.contracts.terminology import CanonicalConceptFamily
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
    CanonicalConceptRegistryError,
)


def concept_definition(
    *,
    concept_id: str = "concept:conditional_copayment",
    canonical_name: str = "Conditional Co-payment",
    domain: str = "health",
    concept_type: str = "COST_SHARING",
    aliases=(),
    customer_phrases=(),
    insurer_terms=(),
    ambiguity_group=None,
    downstream_topic="conditional_copayment",
):
    return CanonicalConceptDefinition(
        concept=CanonicalConceptFamily(
            concept_family_id=concept_id,
            canonical_name=canonical_name,
            definition=f"Definition for {canonical_name}.",
            domain=domain,
        ),
        concept_type=concept_type,
        aliases=tuple(aliases),
        customer_phrases=tuple(customer_phrases),
        insurer_terms=tuple(insurer_terms),
        ambiguity_group=ambiguity_group,
        downstream_topic=downstream_topic,
    )


def test_registry_returns_exact_normalised_alias_candidate():
    definition = concept_definition(aliases=("co-pay", "co payment"))
    registry = CanonicalConceptRegistry((definition,))

    result = registry.candidates_for_phrase("  CO   PAYMENT ", domain="health")

    assert result == (definition,)


def test_registry_matches_customer_phrase_without_product_identity():
    definition = concept_definition(
        customer_phrases=("amount I have to pay myself",),
    )
    registry = CanonicalConceptRegistry((definition,))

    result = registry.candidates_for_phrase(
        "amount i have to pay myself",
        domain="health",
    )

    assert result[0].concept_id == "concept:conditional_copayment"
    assert result[0].downstream_topic == "conditional_copayment"


def test_registry_matches_canonical_name_and_insurer_term():
    definition = concept_definition(insurer_terms=("Customer Share",))
    registry = CanonicalConceptRegistry((definition,))

    assert registry.candidates_for_phrase("conditional co-payment", domain="health") == (
        definition,
    )
    assert registry.candidates_for_phrase("customer share", domain="health") == (
        definition,
    )


def test_unknown_phrase_returns_no_candidates():
    registry = CanonicalConceptRegistry((concept_definition(),))
    assert registry.candidates_for_phrase("unrelated phrase", domain="health") == ()


def test_duplicate_concept_id_is_rejected():
    first = concept_definition()
    second = concept_definition(canonical_name="Another Name")
    with pytest.raises(CanonicalConceptRegistryError, match="duplicate concept_id"):
        CanonicalConceptRegistry((first, second))


def test_duplicate_canonical_name_in_same_domain_is_rejected():
    first = concept_definition(concept_id="concept:a")
    second = concept_definition(concept_id="concept:b")
    with pytest.raises(
        CanonicalConceptRegistryError,
        match="canonical concept names must be unique",
    ):
        CanonicalConceptRegistry((first, second))


def test_shared_alias_requires_explicit_ambiguity_group():
    first = concept_definition(
        concept_id="concept:copayment",
        canonical_name="Co-payment",
        aliases=("customer share",),
    )
    second = concept_definition(
        concept_id="concept:deductible",
        canonical_name="Deductible",
        concept_type="COST_SHARING",
        aliases=("customer share",),
        downstream_topic="deductible",
    )
    with pytest.raises(CanonicalConceptRegistryError, match="ambiguity_group"):
        CanonicalConceptRegistry((first, second))


def test_governed_ambiguity_is_preserved_as_multiple_candidates():
    first = concept_definition(
        concept_id="concept:copayment",
        canonical_name="Co-payment",
        aliases=("customer share",),
        ambiguity_group="customer_cost_share",
    )
    second = concept_definition(
        concept_id="concept:deductible",
        canonical_name="Deductible",
        concept_type="COST_SHARING",
        aliases=("customer share",),
        ambiguity_group="customer_cost_share",
        downstream_topic="deductible",
    )
    registry = CanonicalConceptRegistry((second, first))

    result = registry.candidates_for_phrase("customer share", domain="health")

    assert tuple(item.concept_id for item in result) == (
        "concept:copayment",
        "concept:deductible",
    )


def test_same_phrase_in_different_domains_does_not_create_domain_ambiguity():
    health = concept_definition(
        concept_id="health:waiting_period",
        canonical_name="Waiting Period",
        aliases=("waiting period",),
    )
    life = concept_definition(
        concept_id="life:waiting_period",
        canonical_name="Waiting Period",
        domain="life",
        concept_type="GENERAL_TERM",
        aliases=("waiting period",),
        downstream_topic="waiting_period",
    )
    registry = CanonicalConceptRegistry((health, life))

    assert registry.candidates_for_phrase("waiting period", domain="health") == (health,)
    assert registry.candidates_for_phrase("waiting period", domain="life") == (life,)
    assert tuple(
        item.concept_id for item in registry.candidates_for_phrase("waiting period")
    ) == ("health:waiting_period", "life:waiting_period")


def test_duplicate_normalised_aliases_inside_definition_are_rejected():
    with pytest.raises(CanonicalConceptRegistryError, match="duplicate normalised"):
        concept_definition(aliases=("Co Pay", " co   pay "))


def test_invalid_domain_is_rejected():
    with pytest.raises(CanonicalConceptRegistryError, match="concept.domain"):
        concept_definition(domain="invalid-domain")


def test_registry_order_is_deterministic():
    a = concept_definition(concept_id="concept:a", canonical_name="A")
    b = concept_definition(concept_id="concept:b", canonical_name="B")
    registry = CanonicalConceptRegistry((b, a))
    assert registry.all_concepts() == (a, b)


def test_get_unknown_concept_fails_closed():
    registry = CanonicalConceptRegistry((concept_definition(),))
    with pytest.raises(CanonicalConceptRegistryError, match="not registered"):
        registry.get("concept:missing")
