from knowledge_domains.health.extraction_primitives.currency_sum_insured_parser import (
    CurrencySumInsuredParser,
)


def _source():
    sha256 = "a" * 64
    return {
        "entity_id": "test_insurer:test_product",
        "insurer_id": "test_insurer",
        "document_type": "policy_wording",
        "source_document_id": f"sha256:{sha256}",
        "sha256": sha256,
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


def test_url_less_governed_hash_verified_source_is_accepted():
    source = _source()
    source["source_url"] = None
    source["provenance_status"] = "governed_source_registration_sha256_verified"

    result = CurrencySumInsuredParser().extract_from_pages(
        source=source,
        pages=[{"page_number": 1, "text": "Compassionate Visit up to INR 50,000."}],
    )

    assert result["candidate_count"] == 1
    assert result["source"]["source_url"] is None


def test_url_less_non_governed_source_remains_rejected():
    source = _source()
    source["source_url"] = None

    try:
        CurrencySumInsuredParser().extract_from_pages(
            source=source,
            pages=[{"page_number": 1, "text": "Compassionate Visit up to INR 50,000."}],
        )
    except Exception as exc:
        assert "source_url may be null only for governed SHA-256-verified registration provenance" in str(exc)
    else:
        raise AssertionError("URL-less non-governed source must fail closed")
