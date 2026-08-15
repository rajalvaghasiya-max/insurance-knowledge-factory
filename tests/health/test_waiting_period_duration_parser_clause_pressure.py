from knowledge_domains.health.extraction_primitives.waiting_period_duration_parser import (
    WaitingPeriodDurationParser,
)


def _source():
    sha256 = "b" * 64
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


def test_extracts_code_excl03_duration_from_duration_first_heading():
    result = WaitingPeriodDurationParser().extract_from_pages(
        source=_source(),
        pages=[
            {
                "page_number": 11,
                "text": (
                    "D.1.3 30-day Waiting Period (Code-Excl03) "
                    "Expenses related to treatment of any illness within 30 days from the first policy "
                    "commencement date shall be excluded except claims arising due to an accident."
                ),
            }
        ],
    )

    assert result["candidate_count"] == 1
    candidate = result["candidates"][0]
    assert candidate["attributes"]["waiting_period_category"] == "initial"
    assert candidate["normalized_value"]["value"] == 30
    assert candidate["normalized_value"]["unit"] == "days"


def test_extracts_specified_disease_duration_later_in_same_exclusion_clause_with_pdf_ligature():
    result = WaitingPeriodDurationParser().extract_from_pages(
        source=_source(),
        pages=[
            {
                "page_number": 10,
                "text": (
                    "D.1.2 Speciﬁed disease / procedure Waiting Period: (Code- Excl02) "
                    "Expenses related to the treatment of the listed Conditions, surgeries / treatments "
                    "shall be excluded until the expiry of 24 months of continuous coverage after the date "
                    "of inception of the first policy with us."
                ),
            }
        ],
    )

    assert result["candidate_count"] == 1
    candidate = result["candidates"][0]
    assert candidate["attributes"]["waiting_period_category"] == "specified_disease_or_procedure"
    assert candidate["normalized_value"]["value"] == 24
    assert candidate["normalized_value"]["unit"] == "months"
    assert candidate["attributes"]["normalized_months"] == 24


def test_schedule_delegated_ped_duration_is_not_guessed():
    result = WaitingPeriodDurationParser().extract_from_pages(
        source=_source(),
        pages=[
            {
                "page_number": 10,
                "text": (
                    "D.1.1 Pre-Existing Diseases (Code- Excl01) Expenses related to the treatment of a "
                    "pre-existing Disease and its direct complications shall be excluded until the expiry "
                    "of years / months as specified in the Policy Schedule / Product Benefit Table."
                ),
            }
        ],
    )

    assert result["candidate_count"] == 0
    assert result["status"] == "no_supported_evidence"


def test_unrelated_duration_after_waiting_period_reference_is_not_bound():
    result = WaitingPeriodDurationParser().extract_from_pages(
        source=_source(),
        pages=[
            {
                "page_number": 20,
                "text": (
                    "Waiting Periods under the Policy remain applicable. Claims documents must be submitted "
                    "within 30 days after discharge."
                ),
            }
        ],
    )

    assert result["candidate_count"] == 0
