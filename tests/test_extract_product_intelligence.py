from agents.knowledge_extractor import extract_product_intelligence as extractor


def page(
    text: str,
    *,
    source_type: str = "customer_information_sheet",
    source_file: str = "fixture.json",
    page_number: int = 1,
) -> dict:
    return {
        "source_type": source_type,
        "source_file": source_file,
        "page_number": page_number,
        "text": extractor.normalize(text),
    }


def test_extract_metadata_ignores_placeholder_uin_and_captures_valid_uin():
    pages = [
        page(
            "Product Name: Activ One, "
            "Unique Identification No: XXXXXXXXXXXXXX",
            page_number=1,
        ),
        page(
            "Product UIN: ABC1234567V01",
            source_type="prospectus",
            page_number=2,
        ),
    ]

    metadata = extractor.extract_metadata(pages)

    assert metadata["product_name"] == "Activ One"
    assert metadata["uin"] == "ABC1234567V01"
    assert metadata["uin_candidate"]["source"]["page_number"] == 2


def test_extract_eligibility_rejects_impossible_adult_age_range():
    pages = [
        page(
            "Eligibility and entry age for adults is 5 years to 99 years.",
            page_number=1,
        )
    ]

    eligibility = extractor.extract_eligibility(pages)

    assert "adult_entry_age" not in eligibility
    assert eligibility == {}


def test_extract_discounts_avoids_online_discount_false_positive_from_ppn_text():
    pages = [
        page(
            "Preferred Provider Network (PPN) discount is applicable when treatment "
            "is taken at a listed PPN hospital.",
            source_type="brochure",
            page_number=1,
        )
    ]

    discounts = extractor.extract_discounts(pages)

    assert "online_discount" not in discounts
    assert discounts == {}


def test_extract_discounts_still_detects_explicit_online_discount():
    pages = [
        page(
            "Online discount is available when customers buy online through the "
            "insurer website.",
            source_type="brochure",
            page_number=1,
        )
    ]

    discounts = extractor.extract_discounts(pages)

    assert discounts["online_discount"]["value"] == "Online purchase discount available"
    assert discounts["online_discount"]["validated"] is True


def test_extract_sum_insured_options_extracts_lakh_and_crore_numeric_values():
    pages = [
        page(
            "Sum insured options: Rs. 5,00,000 (5 lakh), "
            "Rs. 10,00,000 (10 lakh), Rs. 1,00,00,000 (1 crore). "
            "Zone wise premium details follow.",
            page_number=1,
        )
    ]

    options = extractor.extract_sum_insured_options(pages)

    assert options["values"] == [500000, 1000000, 10000000]
    assert options["values_raw"] == ["5,00,000", "10,00,000", "1,00,00,000"]
    assert options["validated"] is True
