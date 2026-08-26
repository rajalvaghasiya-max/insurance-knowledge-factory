from __future__ import annotations

from scripts.c5_35_health_object_type_evidence_capture_live import parse_rows


def test_non_life_register_parser_maps_structured_columns() -> None:
    html = """
    <table><tr><th>Archive / Non Archive</th><th>S.no</th><th>Financial Year</th><th>Name of the Insurer</th><th>Product Name</th><th>Type Of Product</th><th>UIN</th><th>Date of Approval</th><th>Documents</th></tr>
    <tr><td>Non-Archived</td><td>GEN2482</td><td>2018-2019</td><td>Example General Insurance</td><td>Example Product</td><td>Main product</td><td>IRDAN999RP0001V01201819</td><td>12-12-2018</td><td>pdf</td></tr></table>
    """
    rows = parse_rows(html)
    assert rows == [{
        "archive_status": "Non-Archived",
        "serial_no": "GEN2482",
        "financial_year": "2018-2019",
        "insurer": "Example General Insurance",
        "product_name": "Example Product",
        "type_of_product": "Main product",
        "uin": "IRDAN999RP0001V01201819",
        "approval_date": "12-12-2018",
    }]


def test_parser_preserves_add_on_value_without_inference() -> None:
    html = """
    <table><tr><td>Non-Archived</td><td>GEN1</td><td>2024-2025</td><td>Example</td><td>Foo</td><td>Add-on</td><td>IRDAN999A0001V01202425</td><td>01-01-2025</td><td>pdf</td></tr></table>
    """
    assert parse_rows(html)[0]["type_of_product"] == "Add-on"


def test_parser_does_not_extract_semantic_document_content() -> None:
    html = """
    <table><tr><td>Non-Archived</td><td>GEN1</td><td>2024-2025</td><td>Example</td><td>Foo</td><td>Main Product</td><td>UIN1</td><td>01-01-2025</td><td><a href='policy.pdf'>Policy wording</a></td></tr></table>
    """
    row = parse_rows(html)[0]
    assert set(row) == {"archive_status", "serial_no", "financial_year", "insurer", "product_name", "type_of_product", "uin", "approval_date"}


def test_header_row_is_ignored() -> None:
    html = """
    <table><tr><th>Archive / Non Archive</th><th>S.no</th><th>Financial Year</th><th>Name of the Insurer</th><th>Product Name</th><th>Type Of Product</th><th>UIN</th><th>Date of Approval</th><th>Documents</th></tr></table>
    """
    assert parse_rows(html) == []
