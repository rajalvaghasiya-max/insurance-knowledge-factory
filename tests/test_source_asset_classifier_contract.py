from __future__ import annotations

import json

import pytest

from agents.product_signal_extractor import ProductSignalExtractor
from agents.source_asset_classifier import SourceAssetClassifier
from agents.uin_candidate_extractor import UinCandidateExtractor


def _write_rules(tmp_path, **overrides):
    payload = {
        "schema_version": "test-1.0",
        "home_paths": ["", "/"],
        "generic_product_slugs": ["products", "health-insurance"],
        "product_listing_slugs": ["health-insurance-plans"],
        "category_url_keywords": ["health-insurance-category"],
        "individual_product_slug_keywords": [
            "arogya-sanjeevani",
            "activ-one",
        ],
        "page_intent_scope_map": {
            "homepage": "institution",
            "customer_service": "institution",
            "calculator": "supporting",
            "faq": "supporting",
            "institution": "institution",
            "document_listing": "document_listing",
            "product_listing": "category",
            "individual_product": "product",
            "claim": "claim",
            "glossary": "supporting",
            "article": "supporting",
            "article_or_product_related": "unknown",
            "article_or_other": "unknown",
        },
    }
    payload.update(overrides)
    path = tmp_path / "source_asset_classification_rules.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_classifier_fails_closed_when_rules_asset_is_missing(tmp_path) -> None:
    missing = tmp_path / "missing_rules.json"

    with pytest.raises(FileNotFoundError, match="classification rules not found"):
        SourceAssetClassifier(rules_path=missing)


def test_classifier_rejects_rules_missing_required_keys(tmp_path) -> None:
    path = _write_rules(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["page_intent_scope_map"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="page_intent_scope_map"):
        SourceAssetClassifier(rules_path=path)


def test_governed_rules_distinguish_product_listing_from_individual_product(tmp_path) -> None:
    classifier = SourceAssetClassifier(rules_path=_write_rules(tmp_path))

    listing = classifier.classify(
        "https://example.test/health-insurance-plans",
        "Health Insurance Plans",
    )
    product = classifier.classify(
        "https://example.test/products/arogya-sanjeevani-policy",
        "Arogya Sanjeevani Policy",
    )

    assert listing["page_intent"] == "product_listing"
    assert listing["asset_scope"] == "category"
    assert product["page_intent"] == "individual_product"
    assert product["asset_scope"] == "product"
    assert product["classification_rules_version"] == "test-1.0"


def test_category_override_is_governed_by_rules_asset(tmp_path) -> None:
    classifier = SourceAssetClassifier(rules_path=_write_rules(tmp_path))

    result = classifier.classify(
        "https://example.test/health-insurance-category/arogya-sanjeevani-policy",
        "Arogya Sanjeevani Policy",
    )

    assert result["page_intent"] == "product_listing"
    assert result["asset_scope"] == "category"
    assert "category URL marker" in result["classification_reason"]


def test_product_signal_extractor_accepts_governed_classifier_dependency(tmp_path) -> None:
    classifier = SourceAssetClassifier(rules_path=_write_rules(tmp_path))
    extractor = ProductSignalExtractor(classifier=classifier)

    assert (
        extractor.detect_page_intent(
            "https://example.test/products/activ-one-max",
            "Activ One Max",
        )
        == "individual_product"
    )


def test_uin_extraction_remains_candidate_only_and_preserves_source_context() -> None:
    candidates = UinCandidateExtractor().extract(
        "Product UIN: ICIHLIP25041V022425",
        source={"url": "https://example.test/product"},
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["uin"] == "ICIHLIP25041V022425"
    assert candidate["candidate_status"] == "format_valid_candidate"
    assert candidate["source"] == {"url": "https://example.test/product"}
    assert "product" not in candidate["source"]
