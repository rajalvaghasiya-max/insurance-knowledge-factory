from __future__ import annotations

from factory_core.governance.preselection_metadata_projection import (
    BlindPreselectionMetadataProjectorV2,
)


def _signals(url: str = "https://example.test/health/products") -> dict:
    return {
        "extractor_version": "0.8",
        "source_parsed_file": "workspace/parsed/semantic-product-name.json",
        "insurer_id": "example_insurer",
        "url": url,
        "page_title": "Example Health Product",
        "content_hash": "abc123",
        "page_intent": "article_or_product_related",
        "asset_scope": "product_related",
        "classification_reason": "metadata catalogue",
        "classification_rules_version": "1.0",
        "product_names": [
            {
                "name": "Example Health Plan",
                "source": "page_title",
                "evidence": "Example Health Plan with waiting period and co-payment details",
            }
        ],
        "uins": ["EXAHLIP26001V012526"],
        "uin_candidates": [
            {
                "uin": "EXAHLIP26001V012526",
                "candidate_status": "format_valid_candidate",
                "extraction_method": "product_uin_label",
                "raw_text": "Product UIN: EXAHLIP26001V012526",
                "evidence_text": "Waiting period 30 days. Co-pay 20%.",
                "source": {
                    "source_parsed_file": "workspace/parsed/semantic-product-name.json",
                    "insurer_id": "example_insurer",
                    "url": url,
                    "content_hash": "abc123",
                    "semantic_excerpt": "20% co-pay",
                },
            }
        ],
        "benefits": [{"evidence": "Benefit mechanics"}],
        "waiting_periods": [{"evidence": "Waiting period 30 days"}],
    }


def _all_text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join([*(str(key) for key in value), *(_all_text(item) for item in value.values())])
    if isinstance(value, list):
        return " ".join(_all_text(item) for item in value)
    return str(value)


def test_v2_projection_contains_no_raw_source_locations() -> None:
    projection = BlindPreselectionMetadataProjectorV2.project(_signals()).to_dict()
    text = _all_text(projection)

    assert projection["schema_version"] == "2.0"
    assert projection["projection_type"] == "blind_preselection_product_metadata_v2"
    assert "source_url" not in projection
    assert "url" not in projection["uin_candidates"][0]["source"]
    assert "source_parsed_file" not in projection["uin_candidates"][0]["source"]
    assert "https://example.test/health/products" not in text
    assert "workspace/parsed/semantic-product-name.json" not in text
    assert projection["source_ref"].startswith("src_sha256:")
    assert projection["uin_candidates"][0]["source"]["source_ref"].startswith("src_sha256:")


def test_v2_source_reference_is_deterministic_but_distinguishes_sources() -> None:
    first = BlindPreselectionMetadataProjectorV2.project(_signals()).to_dict()
    repeat = BlindPreselectionMetadataProjectorV2.project(_signals()).to_dict()
    other = BlindPreselectionMetadataProjectorV2.project(
        _signals("https://example.test/health/other-products")
    ).to_dict()

    assert first["source_ref"] == repeat["source_ref"]
    assert first["source_ref"] != other["source_ref"]
    assert first["uin_candidates"][0]["source"]["source_ref"] != (
        other["uin_candidates"][0]["source"]["source_ref"]
    )


def test_v2_semantic_changes_do_not_change_projection() -> None:
    first = _signals()
    second = _signals()
    second["waiting_periods"] = [{"evidence": "Different waiting mechanic"}]
    second["benefits"] = [{"evidence": "Different benefit mechanic"}]
    second["uin_candidates"][0]["evidence_text"] = "Different semantic evidence"
    second["product_names"][0]["evidence"] = "Different semantic title context"

    assert (
        BlindPreselectionMetadataProjectorV2.project(first).to_dict()
        == BlindPreselectionMetadataProjectorV2.project(second).to_dict()
    )


def test_v2_candidate_provenance_is_identity_only() -> None:
    projection = BlindPreselectionMetadataProjectorV2.project(_signals()).to_dict()
    source = projection["uin_candidates"][0]["source"]

    assert source == {
        "insurer_id": "example_insurer",
        "source_ref": projection["source_ref"],
        "content_hash": "abc123",
    }
    assert set(projection) == {
        "schema_version",
        "projection_type",
        "insurer_id",
        "source_ref",
        "source_content_hash",
        "page_intent",
        "asset_scope",
        "classification_rules_version",
        "product_names",
        "uins",
        "uin_candidates",
    }
