from __future__ import annotations

import json

import pytest

from factory_core.governance.product_identity_currentness_evidence_acquisition import (
    GovernedProductIdentityCurrentnessEvidenceAcquirer,
    ProductIdentityCurrentnessAcquisitionError,
)


def _loader(fixtures: dict[str, dict]):
    calls: list[str] = []

    def load(url: str) -> dict:
        calls.append(url)
        return fixtures[url]

    load.calls = calls  # type: ignore[attr-defined]
    return load


def test_traverses_second_hop_metadata_deterministically_and_extracts_exact_identity() -> None:
    root = "https://insurer.example/downloads"
    child_a = "https://insurer.example/a-product-index"
    child_b = "https://insurer.example/b-product-index"
    loader = _loader(
        {
            root: {
                "artifact_class": "metadata_page",
                "authority_scope": "insurer",
                "text": "Downloads",
                "links": [child_b, child_a],
            },
            child_a: {
                "artifact_class": "insurer_product_index",
                "authority_scope": "insurer",
                "text": (
                    "Product Name: Health Secure Plus\n"
                    "Product UIN: ABCDEHLIP25001V012526\n"
                    "Version: V01\n"
                    "Status: Active\n"
                ),
                "links": [],
            },
            child_b: {
                "artifact_class": "metadata_table",
                "authority_scope": "insurer",
                "text": "Product catalogue",
                "links": [],
            },
        }
    )

    result = GovernedProductIdentityCurrentnessEvidenceAcquirer().acquire(
        insurer_id="example_insurer",
        authorized_start_urls=[root],
        loader=loader,
    ).to_dict()

    assert loader.calls == [root, child_a, child_b]  # type: ignore[attr-defined]
    evidence = result["selector_currentness_evidence"]
    exact = [row for row in evidence if row["binding_status"] == "exact_single_product_single_uin"]
    assert len(exact) == 1
    assert exact[0]["product_names"] == ["Health Secure Plus"]
    assert exact[0]["uins"] == ["ABCDEHLIP25001V012526"]
    assert exact[0]["version_signals"] == ["V01"]
    assert exact[0]["currentness_status"] == "active"


def test_selector_outputs_are_raw_location_free() -> None:
    root = "https://insurer.example/metadata"
    raw_secret = "https://insurer.example/metadata/private-routing-key"
    loader = _loader(
        {
            root: {
                "artifact_class": "metadata_page",
                "authority_scope": "insurer",
                "text": "Metadata landing",
                "links": [raw_secret],
            },
            raw_secret: {
                "artifact_class": "uin_register",
                "authority_scope": "insurer",
                "text": "Product Name: Secure Health\nUIN: ABCDEHLIP25002V012526\nStatus: Current",
                "links": [],
            },
        }
    )

    result = GovernedProductIdentityCurrentnessEvidenceAcquirer().acquire(
        insurer_id="example_insurer",
        authorized_start_urls=[root],
        loader=loader,
    ).to_dict()
    serialized = json.dumps(result, sort_keys=True)

    assert root not in serialized
    assert raw_secret not in serialized
    assert "source_url" not in serialized
    assert "source_parsed_file" not in serialized
    summary = result["acquisition_summary"]
    assert summary["raw_url_fields_emitted"] == 0
    assert summary["raw_anchor_fields_emitted"] == 0
    assert summary["target_clause_reads"] == 0


def test_preserves_content_hash_and_distinct_source_refs_for_corroboration() -> None:
    one = "https://insurer.example/index-a"
    two = "https://regulator.example/index-b"
    shared_text = "Product Name: Secure Health\nUIN: ABCDEHLIP25002V012526\nStatus: Current"
    loader = _loader(
        {
            one: {
                "artifact_class": "insurer_product_index",
                "authority_scope": "insurer",
                "text": shared_text,
                "links": [],
            },
            two: {
                "artifact_class": "regulator_product_index",
                "authority_scope": "regulator",
                "text": shared_text,
                "links": [],
            },
        }
    )

    result = GovernedProductIdentityCurrentnessEvidenceAcquirer(max_depth=0).acquire(
        insurer_id="example_insurer",
        authorized_start_urls=[two, one],
        loader=loader,
    ).to_dict()

    evidence = result["selector_currentness_evidence"]
    assert {row["authority_scope"] for row in evidence} == {"insurer", "regulator"}
    assert len({row["source_ref"] for row in evidence}) == 2
    assert len({row["source_content_hash"] for row in evidence}) == 1


def test_forbidden_policy_wording_is_not_consumed_for_identity_selection() -> None:
    root = "https://insurer.example/downloads"
    wording = "https://insurer.example/policy-wording.pdf"
    loader = _loader(
        {
            root: {
                "artifact_class": "metadata_page",
                "authority_scope": "insurer",
                "text": "Downloads",
                "links": [wording],
            },
            wording: {
                "artifact_class": "policy_wording",
                "authority_scope": "insurer",
                "text": "Product Name: Forbidden Read\nUIN: ABCDEHLIP25003V012526",
                "links": [],
            },
        }
    )

    result = GovernedProductIdentityCurrentnessEvidenceAcquirer().acquire(
        insurer_id="example_insurer",
        authorized_start_urls=[root],
        loader=loader,
    ).to_dict()

    assert result["acquisition_summary"]["rejection_counts"] == {
        "forbidden_artifact_class:policy_wording": 1
    }
    assert all(
        "ABCDEHLIP25003V012526" not in row["uins"]
        for row in result["selector_product_metadata"]
    )


def test_ambiguous_product_uin_binding_fails_closed_in_projection_status() -> None:
    root = "https://insurer.example/product-register"
    loader = _loader(
        {
            root: {
                "artifact_class": "uin_register",
                "authority_scope": "insurer",
                "text": (
                    "Product Name: Health Alpha\n"
                    "Product Name: Health Beta\n"
                    "UIN: ABCDEHLIP25004V012526\n"
                    "UIN: ABCDEHLIP25005V012526\n"
                    "Status: Active\n"
                ),
                "links": [],
            }
        }
    )

    result = GovernedProductIdentityCurrentnessEvidenceAcquirer(max_depth=0).acquire(
        insurer_id="example_insurer",
        authorized_start_urls=[root],
        loader=loader,
    ).to_dict()

    evidence = result["selector_currentness_evidence"][0]
    assert evidence["binding_status"] == "ambiguous_identity_binding"
    assert evidence["currentness_status"] == "active"


def test_conflicting_currentness_signals_fail_closed_as_ambiguous() -> None:
    root = "https://regulator.example/product-index"
    loader = _loader(
        {
            root: {
                "artifact_class": "regulator_product_index",
                "authority_scope": "regulator",
                "text": (
                    "Product Name: Health Alpha\n"
                    "UIN: ABCDEHLIP25004V012526\n"
                    "Status: Active\n"
                    "Status: Withdrawn\n"
                ),
                "links": [],
            }
        }
    )

    result = GovernedProductIdentityCurrentnessEvidenceAcquirer(max_depth=0).acquire(
        insurer_id="example_insurer",
        authorized_start_urls=[root],
        loader=loader,
    ).to_dict()

    assert result["selector_currentness_evidence"][0]["currentness_status"] == "ambiguous"


def test_enforces_depth_and_artifact_bounds() -> None:
    urls = [f"https://insurer.example/{index}" for index in range(5)]
    fixtures = {}
    for index, url in enumerate(urls):
        fixtures[url] = {
            "artifact_class": "metadata_page",
            "authority_scope": "insurer",
            "text": f"Metadata {index}",
            "links": [urls[index + 1]] if index + 1 < len(urls) else [],
        }
    loader = _loader(fixtures)

    result = GovernedProductIdentityCurrentnessEvidenceAcquirer(
        max_depth=2,
        max_artifacts=2,
    ).acquire(
        insurer_id="example_insurer",
        authorized_start_urls=[urls[0]],
        loader=loader,
    ).to_dict()

    assert result["acquisition_summary"]["acquired_artifact_count"] == 2
    assert loader.calls == urls[:2]  # type: ignore[attr-defined]


def test_rejects_invalid_authority_scope_and_invalid_urls() -> None:
    with pytest.raises(ProductIdentityCurrentnessAcquisitionError):
        GovernedProductIdentityCurrentnessEvidenceAcquirer().acquire(
            insurer_id="example_insurer",
            authorized_start_urls=["not-a-url"],
            loader=lambda _url: {},
        )

    root = "https://unknown.example/index"
    with pytest.raises(ProductIdentityCurrentnessAcquisitionError, match="authority_scope"):
        GovernedProductIdentityCurrentnessEvidenceAcquirer(max_depth=0).acquire(
            insurer_id="example_insurer",
            authorized_start_urls=[root],
            loader=lambda _url: {
                "artifact_class": "metadata_page",
                "authority_scope": "unknown",
                "text": "Metadata",
                "links": [],
            },
        )
