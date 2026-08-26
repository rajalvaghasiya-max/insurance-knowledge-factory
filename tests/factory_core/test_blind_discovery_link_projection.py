from __future__ import annotations

import pytest

from factory_core.governance.blind_discovery_link_projection import (
    BlindDiscoveryLinkProjectionError,
    BlindDiscoveryLinkProjector,
)


def _record() -> dict:
    return {
        "source_id": "example_insurer",
        "insurer_id": "example_insurer",
        "source_url": "https://example.test/",
        "discovered_url": "https://example.test/downloads/senior-care-20-percent-copay-waiver",
        "anchor_text": "Senior Care - 20% co-pay waiver after waiting period",
        "page_type": "uin_related",
        "knowledge_value": "high",
        "crawl": True,
        "priority": 1,
        "status": "new",
        "discovery_origin": "captured_html",
        "raw_body_excerpt": "Waiting period 30 days and 20% co-pay apply.",
        "semantic_excerpt": "copayment 20%",
    }


def _all_text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join([*(str(key) for key in value), *(_all_text(item) for item in value.values())])
    if isinstance(value, list):
        return " ".join(_all_text(item) for item in value)
    return str(value)


def test_projection_hides_raw_url_anchor_and_semantic_fields() -> None:
    projection = BlindDiscoveryLinkProjector.project(_record()).to_dict()
    text = _all_text(projection).lower()

    assert projection["projection_type"] == "blind_discovery_link_metadata_v1"
    assert projection["source_id"] == "example_insurer"
    assert projection["page_type"] == "uin_related"
    assert projection["destination_id"].startswith("sha256:")
    assert projection["discovery_record_hash"].startswith("sha256:")

    assert "http" not in text
    assert "senior-care" not in text
    assert "20-percent" not in text
    assert "co-pay" not in text
    assert "waiting period" not in text
    assert "anchor_text" not in projection
    assert "discovered_url" not in projection
    assert "source_url" not in projection
    assert "raw_body_excerpt" not in projection
    assert "semantic_excerpt" not in projection


def test_semantic_anchor_changes_only_record_hash_not_selector_metadata() -> None:
    first = _record()
    second = _record()
    second["anchor_text"] = "Different waiting period and 50% copay semantic text"

    first_projection = BlindDiscoveryLinkProjector.project(first).to_dict()
    second_projection = BlindDiscoveryLinkProjector.project(second).to_dict()

    assert first_projection["destination_id"] == second_projection["destination_id"]
    assert first_projection["page_type"] == second_projection["page_type"]
    assert first_projection["knowledge_value"] == second_projection["knowledge_value"]
    assert first_projection["priority"] == second_projection["priority"]
    assert first_projection["discovery_record_hash"] != second_projection["discovery_record_hash"]


def test_semantic_url_slug_never_crosses_projection() -> None:
    projection = BlindDiscoveryLinkProjector.project(_record()).to_dict()

    assert projection["destination_id"] != _record()["discovered_url"]
    assert "copay" not in _all_text(projection).lower()
    assert "waiver" not in _all_text(projection).lower()


def test_non_metadata_product_detail_is_rejected() -> None:
    record = _record()
    record["page_type"] = "product_or_plan_page"

    with pytest.raises(BlindDiscoveryLinkProjectionError, match="not authorized"):
        BlindDiscoveryLinkProjector.project(record)


def test_policy_wording_is_rejected() -> None:
    record = _record()
    record["page_type"] = "policy_wording_pdf"

    with pytest.raises(BlindDiscoveryLinkProjectionError, match="not authorized"):
        BlindDiscoveryLinkProjector.project(record)


def test_crawl_must_be_explicitly_true() -> None:
    record = _record()
    record["crawl"] = False

    with pytest.raises(BlindDiscoveryLinkProjectionError, match="crawl must be exactly true"):
        BlindDiscoveryLinkProjector.project(record)
