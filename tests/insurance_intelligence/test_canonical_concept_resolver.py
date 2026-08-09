import pytest

from insurance_intelligence.contracts.terminology import CanonicalConceptFamily
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
)
from insurance_intelligence.terminology.concept_resolver import CanonicalConceptResolver


def definition(
    concept_id: str,
    name: str,
    *,
    domain: str = "health",
    aliases=(),
    customer_phrases=(),
    ambiguity_group=None,
    downstream_topic=None,
):
    return CanonicalConceptDefinition(
        concept=CanonicalConceptFamily(
            concept_family_id=concept_id,
            canonical_name=name,
            definition=f"Governed definition for {name}.",
            domain=domain,
        ),
        concept_type="COST_SHARING",
        aliases=tuple(aliases),
        customer_phrases=tuple(customer_phrases),
        ambiguity_group=ambiguity_group,
        downstream_topic=downstream_topic,
    )


def test_exact_alias_resolves_to_one_concept():
    registry = CanonicalConceptRegistry((
        definition(
            "concept:copay",
            "Co-payment",
            aliases=("copay", "co pay"),
            downstream_topic="conditional_copayment",
        ),
    ))
    result = CanonicalConceptResolver(registry).resolve("  CO PAY  ", domain="health")
    assert result.status == "RESOLVED"
    assert result.selected_concept is not None
    assert result.selected_concept.concept_id == "concept:copay"
    assert result.selected_concept.downstream_topic == "conditional_copayment"
    assert result.reason_codes == ("EXACT_GOVERNED_CONCEPT_MATCH",)


def test_customer_phrase_resolves_without_product_identity():
    registry = CanonicalConceptRegistry((
        definition(
            "concept:room-rent-limit",
            "Room rent limit",
            customer_phrases=("room category limit",),
            downstream_topic="coverage",
        ),
    ))
    result = CanonicalConceptResolver(registry).resolve("room category limit")
    assert result.status == "RESOLVED"
    assert result.selected_concept is not None
    assert result.selected_concept.concept_id == "concept:room-rent-limit"


def test_shared_governed_phrase_returns_ambiguous_not_guess():
    registry = CanonicalConceptRegistry((
        definition(
            "concept:copay",
            "Co-payment",
            customer_phrases=("amount I pay myself",),
            ambiguity_group="customer-cost-share",
        ),
        definition(
            "concept:deductible",
            "Deductible",
            customer_phrases=("amount I pay myself",),
            ambiguity_group="customer-cost-share",
        ),
    ))
    result = CanonicalConceptResolver(registry).resolve("amount I pay myself", domain="health")
    assert result.status == "AMBIGUOUS"
    assert result.selected_concept is None
    assert [item.concept_id for item in result.candidates] == [
        "concept:copay",
        "concept:deductible",
    ]
    assert result.reason_codes == ("MULTIPLE_GOVERNED_CONCEPT_MATCHES",)


def test_unknown_phrase_is_not_resolved():
    registry = CanonicalConceptRegistry((definition("concept:copay", "Co-payment"),))
    result = CanonicalConceptResolver(registry).resolve("some unknown insurance phrase", domain="health")
    assert result.status == "NOT_RESOLVED"
    assert result.selected_concept is None
    assert result.candidates == ()
    assert result.reason_codes == ("NO_EXACT_GOVERNED_CONCEPT_MATCH",)


@pytest.mark.parametrize("phrase", (None, "", "   ", 42))
def test_invalid_phrase_returns_invalid_input(phrase):
    result = CanonicalConceptResolver(CanonicalConceptRegistry()).resolve(phrase)
    assert result.status == "INVALID_INPUT"
    assert result.selected_concept is None
    assert result.reason_codes == ("INVALID_PHRASE",)


def test_invalid_domain_returns_invalid_input():
    result = CanonicalConceptResolver(CanonicalConceptRegistry()).resolve("copay", domain="invalid-domain")
    assert result.status == "INVALID_INPUT"
    assert result.reason_codes == ("INVALID_DOMAIN",)


def test_domain_scope_disambiguates_cross_domain_same_phrase():
    registry = CanonicalConceptRegistry((
        definition("concept:health-benefit", "Shared Term", domain="health"),
        definition("concept:motor-benefit", "Shared Term", domain="motor"),
    ))
    health = CanonicalConceptResolver(registry).resolve("Shared Term", domain="health")
    motor = CanonicalConceptResolver(registry).resolve("Shared Term", domain="motor")
    global_result = CanonicalConceptResolver(registry).resolve("Shared Term")
    assert health.status == "RESOLVED"
    assert health.selected_concept.concept_id == "concept:health-benefit"  # type: ignore[union-attr]
    assert motor.status == "RESOLVED"
    assert motor.selected_concept.concept_id == "concept:motor-benefit"  # type: ignore[union-attr]
    assert global_result.status == "AMBIGUOUS"


def test_resolution_id_is_deterministic():
    registry = CanonicalConceptRegistry((definition("concept:copay", "Co-payment", aliases=("copay",)),))
    resolver = CanonicalConceptResolver(registry)
    assert resolver.resolve("copay", domain="health").resolution_id == resolver.resolve("copay", domain="health").resolution_id


def test_resolver_does_not_expose_product_or_recommendation_outputs():
    result = CanonicalConceptResolver(
        CanonicalConceptRegistry((definition("concept:copay", "Co-payment", aliases=("copay",)),))
    ).resolve("copay", domain="health")
    assert not hasattr(result, "product_id")
    assert not hasattr(result, "evidence")
    assert not hasattr(result, "recommendation")
