import json

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_scanner import (
    KnowledgeComponentScanner,
    KnowledgeComponentScannerRunner,
)


def fake_processed_document() -> dict:
    return {
        "document_id": "doc_test",
        "asset_id": "pdoc_test",
        "source": {
            "source_document_type": "policy_wording",
            "authority_score": 90,
        },
        "sections": [
            {
                "section_id": "sec_001",
                "order": 1,
                "title": "Section 1",
                "source": {
                    "page_number": 1,
                    "start_line": 1,
                    "end_line": 8,
                    "section_order": 1,
                },
                "text": (
                    "SECTION 1\n\n"
                    "This processed document fragment preserves raw wording and "
                    "refer Appendix A for related material.\n\n"
                    "1. First structural item only.\n"
                    "2. Second structural item only.\n\n"
                    "Product Name: Activ One Product UIN: ABC1234567V01"
                ),
            }
        ],
        "tables": [
            {
                "table_id": "tbl_001",
                "title": "Illustrative Table",
                "rows": [["Column A", "Column B"], ["Value 1", "Value 2"]],
                "source": {
                    "section_id": "sec_001",
                    "page_number": 1,
                    "section_order": 1,
                },
            }
        ],
    }


def test_scanner_creates_valid_component_collection_from_fake_processed_document():
    collection, report = KnowledgeComponentScanner().scan(
        fake_processed_document(),
        source_asset_path="knowledge/factory/processed_documents/fake.json",
    )
    payload = collection.to_dict()

    assert payload["asset_type"] == "knowledge_component_collection"
    assert payload["department"] == "department_04_knowledge_manufacturing"
    assert payload["production_line"] == "knowledge_component_manufacturing"
    assert payload["engine"] == "KnowledgeComponentScanner"
    assert payload["document_id"] == "doc_test"
    assert payload["processed_document_asset_id"] == "pdoc_test"
    assert payload["source_asset_path"] == (
        "knowledge/factory/processed_documents/fake.json"
    )
    assert payload["components"]
    assert report.components_created == len(payload["components"])
    assert report.source_sections_processed == 1
    assert report.source_tables_processed == 1


def test_scanner_output_includes_required_component_contract_fields():
    collection, _ = KnowledgeComponentScanner().scan(fake_processed_document())
    component = collection.to_dict()["components"][0]

    assert component["component_id"].startswith("kcomp_")
    assert component["component_type"] in {
        "title",
        "paragraph",
        "list_item",
        "table",
        "note",
        "reference",
        "metadata",
        "noise",
    }
    assert isinstance(component["sequence"], int)
    assert component["text"]
    assert component["normalized_text"]
    assert component["source"]["document_id"] == "doc_test"
    assert component["source"]["section_id"] == "sec_001"
    assert "signals" in component
    assert "quality" in component
    assert component["notes"]


def test_scanner_preserves_ordering_with_previous_and_next_component_ids():
    collection, _ = KnowledgeComponentScanner().scan(fake_processed_document())
    components = collection.to_dict()["components"]

    assert [component["sequence"] for component in components] == list(
        range(1, len(components) + 1)
    )
    assert components[0]["previous_component_id"] is None
    assert components[0]["next_component_id"] == components[1]["component_id"]
    assert components[-1]["previous_component_id"] == components[-2]["component_id"]
    assert components[-1]["next_component_id"] is None
    for previous, current, following in zip(components, components[1:], components[2:]):
        assert current["previous_component_id"] == previous["component_id"]
        assert current["next_component_id"] == following["component_id"]


def test_scanner_does_not_perform_insurance_semantic_interpretation():
    collection, _ = KnowledgeComponentScanner().scan(fake_processed_document())
    payload = collection.to_dict()
    semantic_keys = {
        "coverage_type",
        "benefit_type",
        "waiting_period",
        "copay",
        "exclusion",
        "insurance_concept",
    }

    assert payload["statistics"]["department_boundary"] == (
        "raw_components_only_no_semantic_insurance_interpretation"
    )
    for component in payload["components"]:
        assert component["component_type"] not in semantic_keys
        assert semantic_keys.isdisjoint(component["signals"].keys())
        assert any("No insurance semantic interpretation" in note for note in component["notes"])


def test_scanner_runner_writes_collection_and_report_json(tmp_path):
    processed_path = (
        tmp_path
        / "knowledge"
        / "factory"
        / "processed_documents"
        / "fake_processed_document_v2.json"
    )
    processed_path.parent.mkdir(parents=True)
    processed_path.write_text(json.dumps(fake_processed_document()), encoding="utf-8")

    result = KnowledgeComponentScannerRunner(project_root=tmp_path).run(processed_path)

    assert result["collection_path"].exists()
    assert result["report_path"].exists()
    saved_collection = json.loads(result["collection_path"].read_text(encoding="utf-8"))
    saved_report = json.loads(result["report_path"].read_text(encoding="utf-8"))
    assert saved_collection["asset_type"] == "knowledge_component_collection"
    assert saved_report["report_type"] == "knowledge_component_scanner_report"
    assert saved_report["collection_path"] == str(result["collection_path"])
