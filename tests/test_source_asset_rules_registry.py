from agents.product_signal_extractor import ProductSignalExtractor
from agents.source_asset_classifier import SourceAssetClassifier


def test_tracked_source_asset_rules_construct_default_classifier() -> None:
    classifier = SourceAssetClassifier()

    result = classifier.classify(
        "https://example.invalid/health-insurance/arogya-sanjeevani",
        "Arogya Sanjeevani Health Insurance Policy",
    )

    assert result["page_intent"] == "individual_product"
    assert result["asset_scope"] == "product_specific"
    assert result["classification_rules_version"] == "1.0"


def test_product_signal_extractor_constructs_from_tracked_rules() -> None:
    extractor = ProductSignalExtractor()

    result = extractor.classify_source_asset(
        "https://example.invalid/health-insurance-plans",
        "Health Insurance Plans",
    )

    assert result["page_intent"] == "product_listing"
    assert result["asset_scope"] == "category"
