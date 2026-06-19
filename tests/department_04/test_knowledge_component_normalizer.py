import json

from knowledge_domains.health.knowledge_manufacturing.knowledge_component_normalizer import (
    KnowledgeComponentNormalizer,
    KnowledgeComponentNormalizerRunner,
)


def raw_component(
    component_id: str,
    text: str,
    *,
    sequence: int,
    component_type: str = "paragraph",
    section_id: str = "sec_001",
    section_order: int = 1,
    references: list[dict] | None = None,
) -> dict:
    return {
        "component_id": component_id,
        "component_version": "1.0",
        "component_type": component_type,
        "document_id": "doc_test",
        "processed_document_asset_id": "pdoc_test",
        "sequence": sequence,
        "text": text,
        "normalized_text": text.lower(),
        "title_hint": None,
        "source": {
            "document_id": "doc_test",
            "processed_document_asset_id": "pdoc_test",
            "section_id": section_id,
            "section_order": section_order,
            "page_number": 1,
            "start_line": sequence,
            "end_line": sequence,
        },
        "signals": {"structural_signal": component_type},
        "quality": {"confidence": 0.9, "quality_score": 90.0, "warnings": []},
        "references": references or [],
        "notes": ["Raw Knowledge Component scanned from processed document."],
    }


def raw_collection(components: list[dict]) -> dict:
    return {
        "asset_type": "knowledge_component_collection",
        "collection_id": "kcc_test",
        "document_id": "doc_test",
        "processed_document_asset_id": "pdoc_test",
        "components": components,
    }


def normalize_components(components: list[dict]):
    return KnowledgeComponentNormalizer().normalize(raw_collection(components))


def test_normalizer_creates_normalized_component_collection_from_scanner_output():
    collection, report = normalize_components(
        [
            raw_component("kc1", "Definitions", sequence=1, component_type="title"),
            raw_component("kc2", "This is a paragraph.", sequence=2),
        ]
    )
    payload = collection.to_dict()

    assert payload["asset_type"] == "normalized_knowledge_component_collection"
    assert payload["source_collection_id"] == "kcc_test"
    assert payload["department"] == "department_04_knowledge_manufacturing"
    assert payload["components"]
    assert report.raw_components_received == 2
    assert report.normalized_components_created == 2
    assert report.validation_status == "passed"


def test_normalizer_merges_wrapped_continuation_fragments():
    collection, report = normalize_components(
        [
            raw_component("kc1", "The policy provides cover for", sequence=1),
            raw_component("kc2", "eligible expenses described in this section.", sequence=2),
        ]
    )
    component = collection.to_dict()["components"][0]

    assert report.components_merged == 1
    assert len(collection.components) == 1
    assert component["text"] == (
        "The policy provides cover for eligible expenses described in this section."
    )
    assert component["original_component_ids"] == ["kc1", "kc2"]
    assert component["merged_component_ids"] == ["kc2"]
    assert any(
        decision["action"] == "merge_wrapped_fragments"
        for decision in component["normalization_decisions"]
    )


def test_normalizer_downgrades_long_sentence_like_titles_into_paragraphs():
    long_title = (
        "This fragment looks like a sentence because it contains many words "
        "and should not remain a strong title"
    )

    collection, _ = normalize_components(
        [raw_component("kc1", long_title, sequence=1, component_type="title")]
    )
    component = collection.to_dict()["components"][0]

    assert component["original_component_type"] == "title"
    assert component["component_type"] == "paragraph"
    assert any(
        decision["action"] == "downgrade_title_to_paragraph"
        for decision in component["normalization_decisions"]
    )


def test_normalizer_consolidates_duplicates_as_shadow_with_provenance():
    collection, report = normalize_components(
        [
            raw_component("kc1", "Same repeated paragraph.", sequence=1, section_id="sec_001"),
            raw_component("kc2", "Same repeated paragraph.", sequence=2, section_id="sec_002"),
        ]
    )
    components = collection.to_dict()["components"]

    assert report.duplicate_groups == 1
    assert report.duplicate_shadow_components == 1
    assert components[0]["status"] == "active"
    assert components[1]["status"] == "duplicate_shadow"
    assert components[1]["source"]["section_id"] == "sec_002"
    assert components[1]["original_component_ids"] == ["kc2"]
    assert components[0]["duplicate_group_id"] == components[1]["duplicate_group_id"]


def test_normalizer_preserves_original_and_merged_component_ids():
    collection, _ = normalize_components(
        [
            raw_component("kc1", "Wrapped text begins", sequence=1),
            raw_component("kc2", "and continues with traceability.", sequence=2),
        ]
    )
    component = collection.to_dict()["components"][0]

    assert component["original_component_ids"] == ["kc1", "kc2"]
    assert component["merged_component_ids"] == ["kc2"]


def test_normalizer_report_includes_required_metrics_and_boundary():
    _, report = normalize_components(
        [
            raw_component("kc1", "Product Name: Activ One Product UIN: ABC1234567V01", sequence=1),
            raw_component("kc2", "Active paragraph.", sequence=2),
            raw_component("kc3", "Active paragraph.", sequence=3, section_id="sec_002"),
        ]
    )
    report_payload = report.to_dict()

    for key in [
        "raw_components_received",
        "normalized_components_created",
        "components_merged",
        "duplicate_groups",
        "duplicate_shadow_components",
        "noise_components",
        "active_components",
        "quality_score",
        "validation_status",
        "department_boundary",
    ]:
        assert key in report_payload
    assert report_payload["department_boundary"] == (
        "normalized_components_only_no_semantic_insurance_interpretation"
    )


def test_normalizer_splits_multi_definition_components_without_losing_traceability():
    collection, report = normalize_components(
        [
            raw_component(
                "kc_multi",
                "1. Accident: An unforeseen event. 2. AYUSH Hospital: A healthcare facility.",
                sequence=1,
            )
        ]
    )
    components = collection.to_dict()["components"]

    assert report.raw_components_received == 1
    assert report.normalized_components_created == 2
    assert [component["component_type"] for component in components] == [
        "list_item",
        "list_item",
    ]
    assert [component["text"] for component in components] == [
        "1. Accident: An unforeseen event.",
        "2. AYUSH Hospital: A healthcare facility.",
    ]
    assert all(component["original_component_ids"] == ["kc_multi"] for component in components)


def test_repeated_product_name_uin_footer_is_not_active_content():
    collection, report = normalize_components(
        [
            raw_component(
                "kc1",
                "Product Name: Activ One Product UIN: ABC1234567V01",
                sequence=1,
            ),
            raw_component(
                "kc2",
                "Product Name: Activ One Product UIN: ABC1234567V01",
                sequence=2,
                section_id="sec_002",
            ),
        ]
    )
    statuses = [component.status for component in collection.components]

    assert set(statuses).issubset({"metadata", "noise", "duplicate_shadow"})
    assert report.active_components == 0
    assert report.metadata_components + report.noise_components + report.duplicate_shadow_components == 2


def test_cross_references_are_preserved():
    reference = {
        "reference_id": "xref_1",
        "text": "refer Appendix A",
        "normalized_target": "refer_appendix_a",
        "resolved": False,
    }
    collection, report = normalize_components(
        [
            raw_component(
                "kc1",
                "Benefits are subject to limits; refer Appendix A.",
                sequence=1,
                references=[reference],
            )
        ]
    )
    component = collection.to_dict()["components"][0]

    assert component["references"] == [reference]
    assert report.cross_references_preserved == 1


def test_no_components_are_lost_without_traceability():
    raw_components = [
        raw_component("kc1", "First paragraph begins", sequence=1),
        raw_component("kc2", "and continues.", sequence=2),
        raw_component("kc3", "1. Accident: One. 2. AYUSH Hospital: Two.", sequence=3),
        raw_component("kc4", "Same duplicate paragraph.", sequence=4),
        raw_component("kc5", "Same duplicate paragraph.", sequence=5, section_id="sec_002"),
    ]

    collection, _ = normalize_components(raw_components)

    traced_ids = set()
    for component in collection.to_dict()["components"]:
        traced_ids.update(component["original_component_ids"])
        traced_ids.update(component["merged_component_ids"])

    assert {component["component_id"] for component in raw_components}.issubset(traced_ids)


def test_normalizer_runner_writes_collection_and_report_json(tmp_path):
    collection_path = (
        tmp_path
        / "knowledge"
        / "factory"
        / "knowledge_components"
        / "fake_knowledge_component_collection.json"
    )
    collection_path.parent.mkdir(parents=True)
    collection_path.write_text(
        json.dumps(raw_collection([raw_component("kc1", "A paragraph.", sequence=1)])),
        encoding="utf-8",
    )

    result = KnowledgeComponentNormalizerRunner(project_root=tmp_path).run(collection_path)

    assert result["collection_path"].exists()
    assert result["report_path"].exists()
    saved_collection = json.loads(result["collection_path"].read_text(encoding="utf-8"))
    saved_report = json.loads(result["report_path"].read_text(encoding="utf-8"))
    assert saved_collection["asset_type"] == "normalized_knowledge_component_collection"
    assert saved_report["report_type"] == "knowledge_component_normalizer_report"
    assert saved_report["normalized_collection_path"] == str(result["collection_path"])
