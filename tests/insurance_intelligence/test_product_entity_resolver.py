import pytest

from insurance_intelligence.entity_resolution.product_resolver import (
    GovernedProductEntity,
    GovernedProductEntityRegistry,
    ProductEntityRegistryError,
    ProductEntityResolver,
)


def entity(
    *,
    insurer_id: str = "star_health",
    product_id: str = "star_comprehensive",
    name: str = "Star Comprehensive",
    uin: str | None = "SHAHLIP25031V062425",
    aliases: tuple[str, ...] = ("Star Comp",),
    variants: tuple[str, ...] = (),
) -> GovernedProductEntity:
    return GovernedProductEntity(
        canonical_entity_id=f"{insurer_id}:{product_id}",
        insurer_id=insurer_id,
        product_id=product_id,
        canonical_product_name=name,
        uin=uin,
        aliases=aliases,
        product_variants=variants,
    )


def resolver(*entities: GovernedProductEntity) -> ProductEntityResolver:
    return ProductEntityResolver(GovernedProductEntityRegistry(entities))


def test_registry_rejects_entity_id_not_equal_to_insurer_and_product_id() -> None:
    with pytest.raises(ProductEntityRegistryError, match="must equal insurer_id:product_id"):
        GovernedProductEntity(
            canonical_entity_id="wrong:id",
            insurer_id="star_health",
            product_id="star_comprehensive",
            canonical_product_name="Star Comprehensive",
        )


def test_registry_rejects_duplicate_canonical_entity_id() -> None:
    item = entity()
    with pytest.raises(ProductEntityRegistryError, match="duplicate canonical_entity_id"):
        GovernedProductEntityRegistry((item, item))


def test_exact_canonical_entity_id_has_highest_precedence() -> None:
    star = entity(aliases=("shared",))
    other = entity(
        insurer_id="other",
        product_id="shared",
        name="Other Shared",
        uin="OTHERUIN12345",
        aliases=("star_health:star_comprehensive",),
    )
    result = resolver(star, other).resolve("star_health:star_comprehensive")
    assert result.status == "RESOLVED"
    assert result.match_method == "CANONICAL_ENTITY_ID"
    assert result.selected_entity == star


def test_exact_uin_resolves_after_normalisation() -> None:
    star = entity(uin="SHAHLIP25031V062425")
    result = resolver(star).resolve("  shahlip25031v062425  ")
    assert result.status == "RESOLVED"
    assert result.match_method == "UIN"
    assert result.selected_entity == star


def test_governed_alias_resolves_before_canonical_name() -> None:
    first = entity(name="Alpha", aliases=("Star Comprehensive",))
    second = entity(
        insurer_id="other",
        product_id="star_comprehensive",
        name="Star Comprehensive",
        uin="OTHERUIN12345",
        aliases=("Other Star",),
    )
    result = resolver(first, second).resolve("STAR   COMPREHENSIVE")
    assert result.status == "RESOLVED"
    assert result.match_method == "GOVERNED_ALIAS"
    assert result.selected_entity == first


def test_normalised_canonical_product_name_resolves() -> None:
    star = entity(aliases=())
    result = resolver(star).resolve("  STAR   COMPREHENSIVE ")
    assert result.status == "RESOLVED"
    assert result.match_method == "CANONICAL_PRODUCT_NAME"
    assert result.selected_entity == star


def test_shared_alias_fails_closed_as_ambiguous() -> None:
    first = entity(aliases=("Health Plus",))
    second = entity(
        insurer_id="other",
        product_id="health_plus",
        name="Other Health Plus",
        uin="OTHERUIN12345",
        aliases=("health plus",),
    )
    result = resolver(first, second).resolve("Health Plus")
    assert result.status == "AMBIGUOUS"
    assert result.selected_entity is None
    assert result.match_method is None
    assert tuple(item.canonical_entity_id for item in result.candidates) == (
        "other:health_plus",
        "star_health:star_comprehensive",
    )
    assert result.reason_codes == ("MULTIPLE_GOVERNED_ALIAS_MATCHES",)


def test_duplicate_uin_fails_closed_as_ambiguous() -> None:
    first = entity(uin="SHAREDUIN12345", aliases=())
    second = entity(
        insurer_id="other",
        product_id="other_product",
        name="Other Product",
        uin="SHAREDUIN12345",
        aliases=(),
    )
    result = resolver(first, second).resolve("shared uin 12345")
    assert result.status == "AMBIGUOUS"
    assert result.selected_entity is None
    assert result.reason_codes == ("MULTIPLE_UIN_MATCHES",)


def test_unknown_product_is_not_resolved() -> None:
    result = resolver(entity()).resolve("Unknown Gold Policy")
    assert result.status == "NOT_RESOLVED"
    assert result.selected_entity is None
    assert result.candidates == ()
    assert result.reason_codes == ("NO_GOVERNED_PRODUCT_MATCH",)


@pytest.mark.parametrize("value", [None, "", "   ", 123])
def test_invalid_input_is_explicit(value: object) -> None:
    result = resolver(entity()).resolve(value)
    assert result.status == "INVALID_INPUT"
    assert result.selected_entity is None
    assert result.candidates == ()


def test_resolver_does_not_match_product_variants_as_product_identity() -> None:
    star = entity(variants=("Gold", "Platinum"), aliases=())
    result = resolver(star).resolve("Gold")
    assert result.status == "NOT_RESOLVED"


def test_resolution_ids_are_deterministic() -> None:
    service = resolver(entity())
    first = service.resolve("Star Comp")
    second = service.resolve("Star Comp")
    assert first.resolution_id == second.resolution_id
