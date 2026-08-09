from pathlib import Path


SPEC_PATH = Path(
    "docs/architecture/MO_028B_G0_NORMATIVE_INVENTORY_AND_RESIDUE_GATE_SPEC.md"
)


def _spec() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def test_g0_spec_exists_and_is_architecture_first() -> None:
    text = _spec()
    assert "MO-028B.G0" in text
    assert "Normative Inventory & Residue Gate Specification" in text
    assert "G0 does not" in text
    assert "publish new waiting-period facts" in text


def test_g0_forbids_product_identity_bearing_reasoning_code() -> None:
    text = _spec()
    assert "zero product-identity-bearing reasoning code" in text
    assert "Product-identity-bearing branching is not" in text


def test_g0_inventory_is_independent_and_source_anchored() -> None:
    text = _spec()
    assert "Source before schema" in text
    assert "Independent inventory" in text
    assert "High-recall normative inventory path" in text
    assert "Structured semantic mapping path" in text
    assert "OTHER_NORMATIVE_EFFECT" in text


def test_g0_accounts_for_every_normative_unit() -> None:
    text = _spec()
    for state in (
        "MAPPED",
        "MAPPED_AS_RELATIONSHIP",
        "EXPLICITLY_NON_APPLICABLE",
        "DUPLICATE_OR_CORROBORATING",
        "DEFERRED_WITH_REASON",
        "NOT_YET_REPRESENTABLE",
        "CONFLICTED",
        "SOURCE_STALE",
    ):
        assert state in text
    assert "No unaccounted state exists" in text


def test_g0_applicability_is_cross_cutting_and_fine_grained() -> None:
    text = _spec()
    assert "Applicability is a cross-cutting axis" in text
    assert "waiting_period_type × applicability_cell × source/effective-version interval" in text
    assert "optional-reduction-on cell must not block the base initial waiting-period unit" in text


def test_g0_relationships_are_governed_facts() -> None:
    text = _spec()
    for relationship in (
        "MODIFIES",
        "WAIVES",
        "OVERRIDES",
        "DEPENDS_ON",
        "APPLIES_WHEN",
        "INTERACTS_WITH",
        "LIMITED_BY",
    ):
        assert relationship in text
    assert "Relationships require their own evidence accounting and residue handling" in text


def test_g0_authority_includes_regulatory_overlay_and_equal_authority_fail_closed() -> None:
    text = _spec()
    assert "Binding regulatory / statutory overlay" in text
    assert "equal-authority material contradictions fail closed" in text
    assert "contract_fact" in text
    assert "regulatory_overlay" in text
    assert "resulting_effective_interpretation" in text


def test_g0_models_source_and_ontology_lifecycle_separately() -> None:
    text = _spec()
    assert "Ontology lifecycle and source lifecycle are independent" in text
    assert "SOURCE_STALE" in text
    assert "ontology_version" in text
    assert "source_document_version_id" in text
    assert "regulatory_overlay_version" in text


def test_g0_waiting_period_certification_includes_schedule_delegation_and_waiver() -> None:
    text = _spec()
    assert "Schedule-delegated value" in text
    assert "Benefit-scoped waiver relationship" in text
    assert "D.1.1 can delegate duration to the Product Benefit Table" in text


def test_g0_collects_residue_telemetry_without_risk_tiering() -> None:
    text = _spec()
    assert "collect now, act later" in text
    assert "residue_rate" in text
    assert "authority_conflict_count" in text
    assert "MO-029 may use this evidence to design risk-tiered review" in text
