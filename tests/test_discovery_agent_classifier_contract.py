from __future__ import annotations

from agents.discovery_agent import DiscoveryAgent


METADATA_CLASS_TYPES = {
    "download_page",
    "public_disclosure",
    "regulatory",
    "uin_related",
    "withdrawn_products",
}


def test_uin_index_is_metadata_class() -> None:
    agent = DiscoveryAgent()

    result = agent.classify_url(
        url="https://example.test/health-product-uin-list",
        anchor_text="Health product UIN list",
    )

    assert result == "uin_related"
    assert result in METADATA_CLASS_TYPES


def test_public_disclosure_index_is_metadata_class() -> None:
    agent = DiscoveryAgent()

    result = agent.classify_url(
        url="https://example.test/public-disclosure",
        anchor_text="Public Disclosure",
    )

    assert result == "public_disclosure"
    assert result in METADATA_CLASS_TYPES


def test_product_detail_page_is_not_metadata_class() -> None:
    agent = DiscoveryAgent()

    result = agent.classify_url(
        url="https://example.test/health-insurance/senior-care-plan",
        anchor_text="Senior Care Health Insurance Plan",
    )

    assert result == "product_or_plan_page"
    assert result not in METADATA_CLASS_TYPES


def test_semantic_anchor_does_not_turn_product_detail_into_metadata() -> None:
    agent = DiscoveryAgent()

    result = agent.classify_url(
        url="https://example.test/health-insurance/senior-care-plan",
        anchor_text="Senior Care Plan - 20% co-pay waiver",
    )

    assert result == "product_or_plan_page"
    assert result not in METADATA_CLASS_TYPES


def test_semantic_url_slug_does_not_turn_product_detail_into_metadata() -> None:
    agent = DiscoveryAgent()

    result = agent.classify_url(
        url="https://example.test/health/plans/senior-care-20-percent-copay-waiver",
        anchor_text="Senior Care Plan",
    )

    assert result == "product_or_plan_page"
    assert result not in METADATA_CLASS_TYPES


def test_policy_wording_destination_is_not_metadata_class() -> None:
    agent = DiscoveryAgent()

    result = agent.classify_url(
        url="https://example.test/downloads/senior-care-policy-wording.pdf",
        anchor_text="Policy Wording",
    )

    assert result == "policy_wording_pdf"
    assert result not in METADATA_CLASS_TYPES
