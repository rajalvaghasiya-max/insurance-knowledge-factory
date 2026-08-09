from insurance_intelligence.entity_resolution.planner_handoff import (
    ProductEntityPlannerHandoff,
    build_entity_planner_handoff,
)
from insurance_intelligence.entity_resolution.product_resolver import (
    GovernedProductEntity,
    GovernedProductEntityRegistry,
    ProductEntityResolver,
)


def entity(
    *,
    insurer_id: str = "star_health",
    product_id: str = "star_comprehensive",
    name: str = "Star Comprehensive Insurance Policy",
    uin: str = "SHAHLIP26044V092526",
    aliases: tuple[str, ...] = ("Star Comprehensive",),
) -> GovernedProductEntity:
    return GovernedProductEntity(
        canonical_entity_id=f"{insurer_id}:{product_id}",
        insurer_id=insurer_id,
        product_id=product_id,
        canonical_product_name=name,
        uin=uin,
        aliases=aliases,
    )


def test_resolved_entity_becomes_ready_execution_scope() -> None:
    service = ProductEntityResolver(GovernedProductEntityRegistry((entity(),)))
    resolution = service.resolve("Star Comprehensive")

    handoff = build_entity_planner_handoff(resolution)

    assert handoff.status == "READY"
    assert handoff.can_execute is True
    assert handoff.requires_clarification is False
    assert handoff.canonical_entity_id == "star_health:star_comprehensive"
    assert handoff.insurer_id == "star_health"
    assert handoff.product_id == "star_comprehensive"
    assert handoff.uin == "SHAHLIP26044V092526"
    assert handoff.candidate_entity_ids == ("star_health:star_comprehensive",)
    assert handoff.reason_codes == ("GOVERNED_PRODUCT_ENTITY_READY_FOR_PLANNING",)


def test_ambiguous_entity_is_blocked_and_preserves_candidates() -> None:
    first = entity(
        insurer_id="insurer_a",
        product_id="health_secure_a",
        name="Health Secure",
        uin="INSURERA0001",
        aliases=("Health Secure",),
    )
    second = entity(
        insurer_id="insurer_b",
        product_id="health_secure_b",
        name="Health Secure",
        uin="INSURERB0001",
        aliases=("Health Secure",),
    )
    service = ProductEntityResolver(GovernedProductEntityRegistry((first, second)))
    resolution = service.resolve("Health Secure")

    handoff = build_entity_planner_handoff(resolution)

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
    assert handoff.reason_codes == ("ENTITY_REFERENCE_AMBIGUOUS",)


def test_not_resolved_entity_cannot_publish_execution_scope() -> None:
    service = ProductEntityResolver(GovernedProductEntityRegistry((entity(),)))
    resolution = service.resolve("Unknown Product")

    handoff = build_entity_planner_handoff(resolution)

    assert handoff.status == "BLOCKED"
    assert handoff.can_execute is False
    assert handoff.requires_clarification is False
    assert handoff.canonical_entity_id is None
    assert handoff.candidate_entity_ids == ()
    assert handoff.reason_codes == ("UNRESOLVED_ENTITY_REFERENCE",)


def test_invalid_entity_input_cannot_publish_execution_scope() -> None:
    service = ProductEntityResolver(GovernedProductEntityRegistry((entity(),)))
    resolution = service.resolve(123)

    handoff = build_entity_planner_handoff(resolution)

    assert handoff.status == "BLOCKED"
    assert handoff.can_execute is False
    assert handoff.canonical_entity_id is None
    assert handoff.reason_codes == ("INVALID_ENTITY_REFERENCE",)


def test_invalid_handoff_input_is_fail_closed() -> None:
    handoff = build_entity_planner_handoff({"status": "RESOLVED"})

    assert handoff.status == "INVALID_INPUT"
    assert handoff.can_execute is False
    assert handoff.candidate_entity_ids == ()
    assert handoff.reason_codes == ("INVALID_ENTITY_RESOLUTION",)


def test_blocked_handoff_contract_rejects_selected_execution_scope() -> None:
    try:
        ProductEntityPlannerHandoff(
            handoff_id="handoff:test",
            resolution_id="resolution:test",
            status="BLOCKED",
            canonical_entity_id="star_health:star_comprehensive",
            insurer_id="star_health",
            product_id="star_comprehensive",
            uin="SHAHLIP26044V092526",
            candidate_entity_ids=("star_health:star_comprehensive",),
            reason_codes=("ENTITY_REFERENCE_AMBIGUOUS",),
        )
    except ValueError as exc:
        assert "cannot publish an execution scope" in str(exc)
    else:
        raise AssertionError("BLOCKED handoff accepted a selected execution scope")


def test_handoff_contract_contains_no_evidence_or_reasoning_payload() -> None:
    service = ProductEntityResolver(GovernedProductEntityRegistry((entity(),)))
    handoff = build_entity_planner_handoff(service.resolve("Star Comprehensive"))

    assert not hasattr(handoff, "evidence")
    assert not hasattr(handoff, "evidence_spans")
    assert not hasattr(handoff, "finding")
    assert not hasattr(handoff, "recommendation")
    assert not hasattr(handoff, "terminology")


def test_handoff_ids_are_stable() -> None:
    service = ProductEntityResolver(GovernedProductEntityRegistry((entity(),)))
    resolution = service.resolve("Star Comprehensive")

    first = build_entity_planner_handoff(resolution)
    second = build_entity_planner_handoff(resolution)

    assert first.handoff_id == second.handoff_id
