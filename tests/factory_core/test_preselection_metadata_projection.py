from __future__ import annotations

from factory_core.governance.preselection_metadata_projection import (
    BlindPreselectionMetadataProjector,
)


def _signals() -> dict:
    return {
        "extractor_version": "0.8",
        "source_parsed_file": "workspace/parsed/example.json",
        "insurer_id": "example_insurer",
        "url": "https://example.test/health/products",
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
                "evidence_text": "Waiting period 30 days. Product UIN: EXAHLIP26001V012526. Co-pay 20%.",
                "match_start": 24,
                "match_end": 58,
                "source": {
                    "source_parsed_file": "workspace/parsed/example.json",
                    "insurer_id": "example_insurer",
                    "url": "https://example.test/health/products",
                    "content_hash": "abc123",
                    "semantic_excerpt": "20% co-pay",
                },
            }
        ],
        "benefits": [{"evidence": "Benefit mechanics"}],
        "exclusions": [{"evidence": "Exclusion mechanics"}],
        "waiting_periods": [{"evidence": "Waiting period 30 days"}],
        "riders_or_addons": [{"evidence": "Rider"}],
        "sum_insured_values": [{"evidence": "Sum insured"}],
        "premium_values": [{"evidence": "Premium"}],
        "room_rent_limits": [{"evidence": "Room rent"}],
        "claim_process_signals": [{"evidence": "Claims"}],
        "suitability_signals": [{"evidence": "Suitability"}],
    }


def _all_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_all_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(_all_keys(nested))
    return keys


def _all_text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join([*(str(key) for key in value), *(_all_text(item) for item in value.values())])
    if isinstance(value, list):
        return " ".join(_all_text(item) for item in value)
    return str(value)


def test_projection_exposes_only_identity_metadata() -> None:
    projection = BlindPreselectionMetadataProjector.project(_signals()).to_dict()

    assert projection == {
        "schema_version": "1.0",
        "projection_type": "blind_preselection_product_metadata_v1",
        "insurer_id": "example_insurer",
        "source_url": "https://example.test/health/products",
        "source_content_hash": "abc123",
        "page_intent": "article_or_product_related",
        "asset_scope": "product_related",
        "classification_rules_version": "1.0",
        "product_names": ["Example Health Plan"],
        "uins": ["EXAHLIP26001V012526"],
        "uin_candidates": [
            {
                "uin": "EXAHLIP26001V012526",
                "candidate_status": "format_valid_candidate",
                "extraction_method": "product_uin_label",
                "source": {
                    "content_hash": "abc123",
                    "insurer_id": "example_insurer",
                    "source_parsed_file": "workspace/parsed/example.json",
                    "url": "https://example.test/health/products",
                },
            }
        ],
    }


def test_projection_never_exposes_semantic_buckets_or_evidence_windows() -> None:
    projection = BlindPreselectionMetadataProjector.project(_signals()).to_dict()
    keys = _all_keys(projection)
    text = _all_text(projection).lower()

    forbidden_keys = {
        "benefits",
        "exclusions",
        "waiting_periods",
        "riders_or_addons",
        "sum_insured_values",
        "premium_values",
        "room_rent_limits",
        "claim_process_signals",
        "suitability_signals",
        "raw_text",
        "evidence_text",
        "evidence",
        "semantic_excerpt",
    }
    assert keys.isdisjoint(forbidden_keys)
    assert "waiting period 30 days" not in text
    assert "co-pay 20%" not in text
    assert "20% co-pay" not in text


def test_semantic_content_changes_do_not_change_selection_projection() -> None:
    first = _signals()
    second = _signals()
    second["waiting_periods"] = [{"evidence": "Completely different waiting mechanic"}]
    second["benefits"] = [{"evidence": "Completely different benefit"}]
    second["uin_candidates"][0]["evidence_text"] = "Different semantic context around the same UIN"
    second["product_names"][0]["evidence"] = "Different semantic title context"

    assert (
        BlindPreselectionMetadataProjector.project(first).to_dict()
        == BlindPreselectionMetadataProjector.project(second).to_dict()
    )
