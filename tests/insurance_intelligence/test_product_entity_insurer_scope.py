from insurance_intelligence.entity_resolution.product_resolver import (
    GovernedProductEntity,
    GovernedProductEntityRegistry,
    ProductEntityResolver,
)


def entity(
    insurer_id: str,
    product_id: str,
    *,
    name: str = "Health Secure",
    uin: str,
    aliases: tuple[str, ...] = ("Health Secure",),
) -> GovernedProductEntity:
    return GovernedProductEntity(
        canonical_entity_id=f"{insurer_id}:{product_id}",
        insurer_id=insurer_id,
        product_id=product_id,
        canonical_product_name=name,
        uin=uin,
        aliases=aliases,
    )


def service() -> ProductEntityResolver:
    return ProductEntityResolver(
        GovernedProductEntityRegistry(
            (
                entity(
                    "insurer_a",
                    "health_secure_a",
                    uin="AAAHLIP12345678",
                ),
                entity(
                    "insurer_b",
                    "health_secure_b",
                    uin="BBBHLIP12345678",
                ),
                entity(
                    "insurer_a",
                    "other_plan",
                    name="Other Plan",
                    uin="AAAHLIP87654321",
                    aliases=("Other",),
                ),
            )
        )
    )


def test_shared_alias_is_ambiguous_without_insurer_context() -> None:
    result = service().resolve("Health Secure")
    assert result.status == "AMBIGUOUS"
    assert result.selected_entity is None
    assert result.needs_clarification is True
    assert result.clarification_insurer_ids == ("insurer_a", "insurer_b")


def test_insurer_context_narrows_shared_alias_deterministically() -> None:
    result = service().resolve("Health Secure", insurer_id="insurer_b")
    assert result.status == "RESOLVED"
    assert result.selected_entity is not None
    assert result.selected_entity.canonical_entity_id == "insurer_b:health_secure_b"
    assert result.match_method == "GOVERNED_ALIAS"
    assert result.needs_clarification is False
    assert result.clarification_insurer_ids == ()


def test_insurer_context_narrows_shared_canonical_name_deterministically() -> None:
    first = GovernedProductEntity(
        canonical_entity_id="insurer_a:alpha",
        insurer_id="insurer_a",
        product_id="alpha",
        canonical_product_name="Common Plan",
        uin="AAAHLIP11111111",
    )
    second = GovernedProductEntity(
        canonical_entity_id="insurer_b:beta",
        insurer_id="insurer_b",
        product_id="beta",
        canonical_product_name="Common Plan",
        uin="BBBHLIP22222222",
    )
    resolver = ProductEntityResolver(GovernedProductEntityRegistry((first, second)))

    global_result = resolver.resolve("Common Plan")
    scoped_result = resolver.resolve("Common Plan", insurer_id="insurer_a")

    assert global_result.status == "AMBIGUOUS"
    assert global_result.clarification_insurer_ids == ("insurer_a", "insurer_b")
    assert scoped_result.status == "RESOLVED"
    assert scoped_result.selected_entity == first
    assert scoped_result.match_method == "CANONICAL_PRODUCT_NAME"


def test_wrong_insurer_context_does_not_allow_unique_uin_to_bypass_scope() -> None:
    result = service().resolve("BBBHLIP12345678", insurer_id="insurer_a")
    assert result.status == "NOT_RESOLVED"
    assert result.selected_entity is None
    assert result.reason_codes == ("NO_GOVERNED_PRODUCT_MATCH_IN_INSURER_CONTEXT",)


def test_wrong_insurer_context_does_not_allow_canonical_entity_id_to_bypass_scope() -> None:
    result = service().resolve(
        "insurer_b:health_secure_b",
        insurer_id="insurer_a",
    )
    assert result.status == "NOT_RESOLVED"
    assert result.selected_entity is None


def test_unregistered_insurer_context_fails_closed() -> None:
    result = service().resolve("Health Secure", insurer_id="insurer_unknown")
    assert result.status == "NOT_RESOLVED"
    assert result.reason_codes == ("INSURER_CONTEXT_NOT_REGISTERED",)


def test_invalid_insurer_context_is_invalid_input() -> None:
    result = service().resolve("Health Secure", insurer_id="   ")
    assert result.status == "INVALID_INPUT"
    assert result.reason_codes == ("INVALID_INSURER_CONTEXT",)


def test_insurer_context_does_not_match_product_variants() -> None:
    entity_with_variant = GovernedProductEntity(
        canonical_entity_id="insurer_a:variant_plan",
        insurer_id="insurer_a",
        product_id="variant_plan",
        canonical_product_name="Variant Plan",
        uin="AAAHLIP33333333",
        product_variants=("Gold",),
    )
    resolver = ProductEntityResolver(
        GovernedProductEntityRegistry((entity_with_variant,))
    )

    result = resolver.resolve("Gold", insurer_id="insurer_a")
    assert result.status == "NOT_RESOLVED"
