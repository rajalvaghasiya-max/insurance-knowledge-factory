import copy
import json
from pathlib import Path

import pytest

from insurance_intelligence.entity_resolution.product_resolver import ProductEntityResolver
from insurance_intelligence.entity_resolution.registry_adapter import (
    ProductIdentityRegistryAdapterError,
    build_runtime_registry_from_references,
    governed_entity_from_reference,
    load_runtime_registry_from_files,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
STAR_SPEC = REPO_ROOT / "docs" / "architecture" / "star_health_star_comprehensive_product_identity_reference_spec.json"
BAJAJ_SPEC = REPO_ROOT / "docs" / "architecture" / "bajaj_my_health_care_product_identity_reference_spec.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_real_governed_health_identity_specs_build_runtime_registry() -> None:
    registry = load_runtime_registry_from_files((STAR_SPEC, BAJAJ_SPEC))
    ids = tuple(item.canonical_entity_id for item in registry.all_entities())
    assert ids == (
        "bajaj_allianz_general:my_health_care",
        "star_health:star_comprehensive",
    )


def test_star_resolves_by_canonical_entity_id() -> None:
    resolver = ProductEntityResolver(load_runtime_registry_from_files((STAR_SPEC, BAJAJ_SPEC)))
    result = resolver.resolve("star_health:star_comprehensive")
    assert result.status == "RESOLVED"
    assert result.match_method == "CANONICAL_ENTITY_ID"
    assert result.selected_entity is not None
    assert result.selected_entity.uin == "SHAHLIP26044V092526"


def test_star_resolves_by_real_uin() -> None:
    resolver = ProductEntityResolver(load_runtime_registry_from_files((STAR_SPEC, BAJAJ_SPEC)))
    result = resolver.resolve("SHAHLIP26044V092526")
    assert result.status == "RESOLVED"
    assert result.match_method == "UIN"
    assert result.selected_entity is not None
    assert result.selected_entity.canonical_entity_id == "star_health:star_comprehensive"


def test_bajaj_resolves_by_governed_alias() -> None:
    resolver = ProductEntityResolver(load_runtime_registry_from_files((STAR_SPEC, BAJAJ_SPEC)))
    result = resolver.resolve("My Health Care Plan1")
    assert result.status == "RESOLVED"
    assert result.match_method == "GOVERNED_ALIAS"
    assert result.selected_entity is not None
    assert result.selected_entity.canonical_entity_id == "bajaj_allianz_general:my_health_care"


def test_adapter_preserves_identity_but_not_evidence_payloads() -> None:
    star = governed_entity_from_reference(_load(STAR_SPEC))
    assert star.canonical_entity_id == "star_health:star_comprehensive"
    assert star.canonical_product_name == "Star Comprehensive Insurance Policy"
    assert star.uin == "SHAHLIP26044V092526"
    assert not hasattr(star, "identity_evidence")
    assert not hasattr(star, "evidence")
    assert not hasattr(star, "review_rationale")


def test_non_human_reviewed_reference_is_rejected() -> None:
    spec = copy.deepcopy(_load(STAR_SPEC))
    spec["reviewed_by_human"] = False
    with pytest.raises(ProductIdentityRegistryAdapterError, match="human reviewed"):
        governed_entity_from_reference(spec)


def test_reference_without_exact_uin_evidence_is_rejected() -> None:
    spec = copy.deepcopy(_load(STAR_SPEC))
    spec["identity_evidence"] = [
        item for item in spec["identity_evidence"] if item["signal_type"] != "uin_exact_match"
    ]
    with pytest.raises(ProductIdentityRegistryAdapterError, match="uin_exact_match"):
        governed_entity_from_reference(spec)


def test_reference_without_manual_review_signal_is_rejected() -> None:
    spec = copy.deepcopy(_load(STAR_SPEC))
    spec["identity_evidence"] = [
        item for item in spec["identity_evidence"] if item["signal_type"] != "manual_product_review"
    ]
    with pytest.raises(ProductIdentityRegistryAdapterError, match="manual_product_review"):
        governed_entity_from_reference(spec)


def test_adapter_rejects_entity_id_inconsistent_with_insurer_and_product() -> None:
    spec = copy.deepcopy(_load(STAR_SPEC))
    spec["product_identity"]["entity_id"] = "star_health:wrong_product"
    with pytest.raises(ProductIdentityRegistryAdapterError, match="insurer_id:product_id"):
        governed_entity_from_reference(spec)


def test_duplicate_runtime_entity_ids_fail_closed() -> None:
    star = _load(STAR_SPEC)
    duplicate = copy.deepcopy(star)
    duplicate["product_identity"]["uin"] = "SHAHLIP99999V012526"
    with pytest.raises(ProductIdentityRegistryAdapterError, match="duplicate canonical_entity_id"):
        build_runtime_registry_from_references((star, duplicate))
