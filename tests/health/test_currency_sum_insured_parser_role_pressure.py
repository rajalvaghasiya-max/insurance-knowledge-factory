from knowledge_domains.health.extraction_primitives.currency_sum_insured_parser import (
    CurrencySumInsuredParser,
)


def _source():
    return {
        "entity_id": "test_insurer:test_product",
        "insurer_id": "test_insurer",
        "document_type": "policy_wording",
        "source_document_id": "test_doc",
        "sha256": "a" * 64,
        "source_url": "https://example.test/policy.pdf",
        "source_page_url": "https://example.test/product",
        "relative_archive_path": "archive/test/policy.pdf",
        "provenance_status": "registered",
    }


def test_immediate_up_to_limit_outranks_later_premium_word():
    parser = CurrencySumInsuredParser()
    result = parser.extract_from_pages(
        source=_source(),
        pages=[
            {
                "page_number": 1,
                "text": (
                    "Family Visit For SI upto 10 lacs– Upto INR 25,000 "
                    "Renewal premium waiver benefit in case of death of proposer Applicable"
                ),
            }
        ],
    )

    assert result["candidate_count"] == 1
    candidate = result["candidates"][0]
    assert candidate["normalized_value"]["value"] == 25000
    assert candidate["attributes"]["monetary_role_hint"] == "sub_limit_or_limit"
    assert "sum_insured_band_reference" in candidate["attributes"]["condition_hints"]


def test_plain_premium_amount_remains_premium_without_immediate_limit_phrase():
    parser = CurrencySumInsuredParser()
    result = parser.extract_from_pages(
        source=_source(),
        pages=[
            {
                "page_number": 1,
                "text": "Renewal premium payable is INR 25,000 for the policy year.",
            }
        ],
    )

    assert result["candidate_count"] == 1
    assert result["candidates"][0]["attributes"]["monetary_role_hint"] == "premium"
