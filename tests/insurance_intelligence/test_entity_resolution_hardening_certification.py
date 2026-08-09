from insurance_intelligence.entity_resolution.planner_handoff import (
    build_entity_planner_handoff,
)
from insurance_intelligence.entity_resolution.product_resolver import (
    GovernedProductEntity,
    GovernedProductEntityRegistry,
    ProductEntityResolver,
)


def _entity(
    insurer_id: str,
    product_id: str,
    name: str,
    *,
    uin: str | None = None,
    aliases: tuple[str, ...] = (),
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


def test_canonical_entity_id_precedence_cannot_be_shadowed_by_alias() -> None:
    canonical = _entity(
        "star_health",
        "star_comprehensive",
        "Star Comprehensive Insurance Policy",
        uin="SHAHLIP26044V092526",
    )
    shadow = _entity(
        "other_insurer",
        "other_product",
        "Other Product",
        uin="OTHHLIP26044V092526",
        aliases=("star_health:star_comprehensive",),
    )
    result = ProductEntityResolver(
        GovernedProductEntityRegistry((canonical, shadow))
    ).resolve("star_health:star_comprehensive")

    assert result.status == "RESOLVED"
    assert result.match_method == "CANONICAL_ENTITY_ID"
    assert result.selected_entity == canonical


def test_uin_precedence_cannot_be_shadowed_by_alias() -> None:
    by_uin = _entity(
        "star_health",
        "star_comprehensive",
        "Star Comprehensive Insurance Policy",
        uin="SHAHLIP26044V092526",
    )
    alias_shadow = _entity(
        "other_insurer",
        "other_product",
        "Other Product",
        uin="OTHHLIP26044V092526",
        aliases=("SHAHLIP26044V092526",),
    )
    result = ProductEntityResolver(
        GovernedProductEntityRegistry((by_uin, alias_shadow))
    ).resolve("SHAHLIP26044V092526")

    assert result.status == "RESOLVED"
    assert result.match_method == "UIN"
    assert result.selected_entity == by_uin


def test_duplicate_uin_across_insurers_is_ambiguous_without_context() -> None:
    first = _entity(
        "insurer_a",
        "health_secure_a",
        "Health Secure A",
        uin="SHAREDUIN12345",
    )
    second = _entity(
        "insurer_b",
        "health_secure_b",
        "Health Secure B",
        uin="SHAREDUIN12345",
    )
    resolver = ProductEntityResolver(GovernedProductEntityRegistry((first, second)))

    result = resolver.resolve("SHAREDUIN12345")

    assert result.status == "AMBIGUOUS"
    assert result.selected_entity is None
    assert result.match_method is None
    assert tuple(item.canonical_entity_id for item in result.candidates) == (
        "insurer_a:health_secure_a",
        "insurer_b:health_secure_b",
    )


def test_duplicate_uin_can_be_narrowed_only_by_exact_insurer_context() -> None:
    first = _entity(
        "insurer_a",
        "health_secure_a",
        "Health Secure A",
        uin="SHAREDUIN12345",
    )
    second = _entity(
        "insurer_b",
        "health_secure_b",
        "Health Secure B",
        uin="SHAREDUIN12345",
    )
    resolver = ProductEntityResolver(GovernedProductEntityRegistry((first, second)))

    result = resolver.resolve("SHAREDUIN12345", insurer_id="insurer_b")

    assert result.status == "RESOLVED"
    assert result.match_method == "UIN"
    assert result.selected_entity == second


def test_shared_alias_within_same_insurer_remains_ambiguous() -> None:
    first = _entity(
        "insurer_a",
        "product_one",
        "Product One",
        uin="INSAA1111111",
        aliases=("Health Secure",),
    )
    second = _entity(
        "insurer_a",
        "product_two",
        "Product Two",
        uin="INSAA2222222",
        aliases=("Health Secure",),
    )
    resolver = ProductEntityResolver(GovernedProductEntityRegistry((first, second)))

    result = resolver.resolve("Health Secure", insurer_id="insurer_a")

    assert result.status == "AMBIGUOUS"
    assert result.needs_clarification is True
    assert result.clarification_insurer_ids == ("insurer_a",)
    assert result.selected_entity is None


def test_variant_name_never_resolves_as_product_identity() -> None:
    entity = _entity(
        "insurer_a",
        "health_secure",
        "Health Secure",
        uin="INSAA3333333",
        variants=("Gold", "Platinum"),
    )
    result = ProductEntityResolver(
        GovernedProductEntityRegistry((entity,))
    ).resolve("Gold")

    assert result.status == "NOT_RESOLVED"
    assert result.selected_entity is None


def test_wrong_insurer_context_blocks_even_exact_canonical_entity_id() -> None:
    entity = _entity(
        "star_health",
        "star_comprehensive",
        "Star Comprehensive Insurance Policy",
        uin="SHAHLIP26044V092526",
    )
    result = ProductEntityResolver(
        GovernedProductEntityRegistry((entity,))
    ).resolve(
        "star_health:star_comprehensive",
        insurer_id="other_insurer",
    )

    assert result.status == "NOT_RESOLVED"
    assert result.selected_entity is None


def test_wrong_insurer_context_blocks_even_exact_uin() -> None:
    entity = _entity(
        "star_health",
        "star_comprehensive",
        "Star Comprehensive Insurance Policy",
        uin="SHAHLIP26044V092526",
    )
    result = ProductEntityResolver(
        GovernedProductEntityRegistry((entity,))
    ).resolve("SHAHLIP26044V092526", insurer_id="other_insurer")

    assert result.status == "NOT_RESOLVED"
    assert result.selected_entity is None


def test_ambiguous_resolution_cannot_cross_planner_handoff() -> None:
    first = _entity(
        "insurer_a",
        "health_secure_a",
        "Health Secure A",
        uin="INSAA4444444",
        aliases=("Health Secure",),
    )
    second = _entity(
        "insurer_b",
        "health_secure_b",
        "Health Secure B",
        uin="INSBB4444444",
        aliases=("Health Secure",),
    )
    resolution = ProductEntityResolver(
        GovernedProductEntityRegistry((first, second))
    ).resolve("Health Secure")

    handoff = build_entity_planner_handoff(resolution)

    assert resolution.status == "AMBIGUOUS"
    assert handoff.status == "BLOCKED"
    assert handoff.can_execute is False
    assert handoff.requires_clarification is True
    assert handoff.canonical_entity_id is None
    assert handoff.insurer_id is None
    assert handoff.product_id is None
    assert handoff.uin is None
    assert handoff.candidate_entity_ids == (
        "insurer_a:health_secure_a",
        "insurer_b:health_secure_b",
    )


def test_not_resolved_identity_cannot_cross_planner_handoff() -> None:
    entity = _entity(
        "star_health",
        "star_comprehensive",
        "Star Comprehensive Insurance Policy",
        uin="SHAHLIP26044V092526",
    )
    resolution = ProductEntityResolver(
        GovernedProductEntityRegistry((entity,))
    ).resolve("Unknown Product")

    handoff = build_entity_planner_handoff(resolution)

    assert resolution.status == "NOT_RESOLVED"
    assert handoff.status == "BLOCKED"
    assert handoff.can_execute is False
    assert handoff.candidate_entity_ids == ()
    assert handoff.reason_codes == ("UNRESOLVED_ENTITY_REFERENCE",)


def test_unique_governed_identity_is_only_path_to_ready_handoff() -> None:
    entity = _entity(
        "star_health",
        "star_comprehensive",
        "Star Comprehensive Insurance Policy",
        uin="SHAHLIP26044V092526",
        aliases=("Star Comprehensive",),
    )
    resolution = ProductEntityResolver(
        GovernedProductEntityRegistry((entity,))
    ).resolve("Star Comprehensive")

    handoff = build_entity_planner_handoff(resolution)

    assert resolution.status == "RESOLVED"
    assert handoff.status == "READY"
    assert handoff.can_execute is True
    assert handoff.canonical_entity_id == "star_health:star_comprehensive"
    assert handoff.insurer_id == "star_health"
    assert handoff.product_id == "star_comprehensive"
    assert handoff.uin == "SHAHLIP26044V092526"
    assert handoff.candidate_entity_ids == ("star_health:star_comprehensive",)
