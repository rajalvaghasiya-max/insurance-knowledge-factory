import copy
import json
from pathlib import Path

import pytest

from insurance_intelligence.entity_resolution.product_resolver import ProductEntityResolver
from insurance_intelligence.entity_resolution.registry_adapter import (
    ProductIdentityRegistryAdapterError,
    governed_entity_from_reference,
    load_runtime_registry_from_files,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIV_ONE_SPEC = (
    REPO_ROOT
    / "docs"
    / "architecture"
    / "aditya_birla_activ_one_product_identity_reference_spec.json"
)


def _load() -> dict:
    return json.loads(ACTIV_ONE_SPEC.read_text(encoding="utf-8"))


def test_activ_one_reference_is_human_reviewed_and_governed() -> None:
    spec = _load()
    assert spec["reviewed_by_human"] is True
    assert spec["product_identity"] == {
        "entity_id": "aditya_birla_health:activ_one",
        "insurer_id": "aditya_birla_health",
        "product_id": "activ_one",
        "canonical_product_name": "Activ One",
        "uin": "ADIHLIP24097V012324",
    }
    assert any(
        item["signal_type"] == "manual_product_review"
        and item["verification"] == "manual_reviewed"
        for item in spec["identity_evidence"]
    )


def test_activ_one_reference_builds_runtime_entity() -> None:
    entity = governed_entity_from_reference(_load())
    assert entity.canonical_entity_id == "aditya_birla_health:activ_one"
    assert entity.insurer_id == "aditya_birla_health"
    assert entity.product_id == "activ_one"
    assert entity.canonical_product_name == "Activ One"
    assert entity.uin == "ADIHLIP24097V012324"


def test_activ_one_resolves_by_canonical_entity_id() -> None:
    resolver = ProductEntityResolver(load_runtime_registry_from_files((ACTIV_ONE_SPEC,)))
    result = resolver.resolve("aditya_birla_health:activ_one")
    assert result.status == "RESOLVED"
    assert result.match_method == "CANONICAL_ENTITY_ID"
    assert result.selected_entity is not None
    assert result.selected_entity.uin == "ADIHLIP24097V012324"


def test_activ_one_resolves_by_uin() -> None:
    resolver = ProductEntityResolver(load_runtime_registry_from_files((ACTIV_ONE_SPEC,)))
    result = resolver.resolve("ADIHLIP24097V012324")
    assert result.status == "RESOLVED"
    assert result.match_method == "UIN"
    assert result.selected_entity is not None
    assert result.selected_entity.canonical_entity_id == "aditya_birla_health:activ_one"


def test_activ_one_resolves_by_canonical_product_name() -> None:
    resolver = ProductEntityResolver(load_runtime_registry_from_files((ACTIV_ONE_SPEC,)))
    result = resolver.resolve("Activ One")
    assert result.status == "RESOLVED"
    assert result.selected_entity is not None
    assert result.selected_entity.canonical_entity_id == "aditya_birla_health:activ_one"


def test_activ_one_reference_without_manual_review_fails_closed() -> None:
    spec = copy.deepcopy(_load())
    spec["identity_evidence"] = [
        item
        for item in spec["identity_evidence"]
        if item["signal_type"] != "manual_product_review"
    ]
    with pytest.raises(ProductIdentityRegistryAdapterError, match="manual_product_review"):
        governed_entity_from_reference(spec)


def test_activ_one_reference_without_uin_evidence_fails_closed() -> None:
    spec = copy.deepcopy(_load())
    spec["identity_evidence"] = [
        item
        for item in spec["identity_evidence"]
        if item["signal_type"] != "uin_exact_match"
    ]
    with pytest.raises(ProductIdentityRegistryAdapterError, match="uin_exact_match"):
        governed_entity_from_reference(spec)
