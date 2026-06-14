import json
import sys
from pathlib import Path

import pytest

from knowledge_domains.health.routing import evidence_router
from knowledge_domains.health.routing.evidence_router import EvidenceRouter
from scripts import run_evidence_router


ENTITY_ID = "aditya_birla_health:activ_one"


@pytest.fixture
def isolated_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_router, "BASE_DIR", tmp_path)
    monkeypatch.setattr(run_evidence_router, "BASE_DIR", tmp_path)
    return tmp_path


def write_text_file(base_dir: Path, relative_path: str, text: str) -> Path:
    path = base_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_json_file(base_dir: Path, relative_path: str, data: dict) -> Path:
    path = base_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_product_aware_filtering_keeps_correct_entity_documents(isolated_base_dir):
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "policy_wording_activ_one.txt",
        "Aditya Birla Health Activ One policy wording with copay details.",
    )
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/generic/documents/"
        "generic_healthinsurance_page.txt",
        "Aditya Birla Health healthinsurance generic page without product token.",
    )

    plan = EvidenceRouter().resolve_search_plan(
        entity_id=ENTITY_ID,
        field="copay",
        base_roots=["knowledge"],
    )

    assert plan["candidate_count"] == 1
    assert plan["candidates"][0]["relative_path"] == (
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "policy_wording_activ_one.txt"
    )
    assert plan["candidates"][0]["match_reason"] == "strong_product_match"
    assert plan["rejected_counts"]["not_entity_match"] == 1


def test_wrong_insurer_or_product_documents_are_rejected(isolated_base_dir):
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "policy_wording_activ_one.txt",
        "Aditya Birla Health Activ One policy wording with copay details.",
    )
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one_max/documents/"
        "policy_wording_activ_one_max.txt",
        "Aditya Birla Health Activ One Max policy wording with copay details.",
    )
    write_text_file(
        isolated_base_dir,
        "knowledge/health/star_health/star_comprehensive/documents/policy_wording.txt",
        "Star Health comprehensive policy wording with copay details.",
    )

    plan = EvidenceRouter().resolve_search_plan(
        entity_id=ENTITY_ID,
        field="copay",
        base_roots=["knowledge"],
    )

    assert [candidate["relative_path"] for candidate in plan["candidates"]] == [
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "policy_wording_activ_one.txt"
    ]
    assert plan["rejected_counts"]["not_entity_match"] == 2


def test_source_priority_ordering_is_respected(isolated_base_dir):
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one/html_sections/"
        "activ_one_page.txt",
        "Aditya Birla Health Activ One webpage with copay details.",
    )
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "activ_one_brochure.txt",
        "Aditya Birla Health Activ One brochure with copay details.",
    )
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "activ_one_customer_information_sheet.txt",
        "Aditya Birla Health Activ One customer information sheet with copay details.",
    )
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "activ_one_policy_wording.txt",
        "Aditya Birla Health Activ One policy wording with copay details.",
    )

    plan = EvidenceRouter().resolve_search_plan(
        entity_id=ENTITY_ID,
        field="copay",
        base_roots=["knowledge"],
    )

    assert [candidate["source_type"] for candidate in plan["candidates"]] == [
        "policy_wording",
        "customer_information_sheet",
        "brochure",
        "webpage",
    ]


def test_blocked_context_rejection_works_when_supported(isolated_base_dir):
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "policy_wording_activ_one.txt",
        "Aditya Birla Health Activ One policy wording with copay details.",
    )
    write_text_file(
        isolated_base_dir,
        "archive/aditya_birla_health/travel-insurance/activ_one_policy_wording.txt",
        "Aditya Birla Health Activ One travel-insurance page with copay details.",
    )

    plan = EvidenceRouter().resolve_search_plan(
        entity_id=ENTITY_ID,
        field="copay",
        base_roots=["knowledge", "archive"],
    )

    assert plan["candidate_count"] == 1
    assert plan["candidates"][0]["relative_path"] == (
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "policy_wording_activ_one.txt"
    )
    assert plan["rejected_counts"]["blocked_context"] == 1


def test_json_metadata_can_match_product_and_classify_source(isolated_base_dir):
    write_json_file(
        isolated_base_dir,
        "archive/metadata/aditya_birla_health_activ_one_cis.json",
        {
            "title": "Aditya Birla Health Activ One",
            "document_type": "Customer Information Sheet",
            "url": "https://example.test/healthinsurance/activ-one/cis",
        },
    )

    plan = EvidenceRouter().resolve_search_plan(
        entity_id=ENTITY_ID,
        field="copay",
        base_roots=["archive"],
    )

    assert plan["candidate_count"] == 1
    assert plan["candidates"][0]["source_type"] == "customer_information_sheet"
    assert plan["candidates"][0]["match_reason"] == "strong_product_match"


def test_run_evidence_router_writes_routing_plan_output(
    isolated_base_dir,
    monkeypatch,
):
    write_text_file(
        isolated_base_dir,
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "policy_wording_activ_one.txt",
        "Aditya Birla Health Activ One policy wording with copay details.",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_evidence_router.py",
            "--entity-id",
            ENTITY_ID,
            "--field",
            "copay",
            "--base-roots",
            "knowledge",
        ],
    )

    run_evidence_router.main()

    output_path = (
        isolated_base_dir
        / "knowledge"
        / "health"
        / "routing_plans"
        / "aditya_birla_health_activ_one_copay_routing_plan.json"
    )
    plan = json.loads(output_path.read_text(encoding="utf-8"))

    assert plan["entity_id"] == ENTITY_ID
    assert plan["field"] == "copay"
    assert plan["router_version"] == EvidenceRouter.VERSION
    assert plan["candidate_count"] == 1
    assert plan["candidates"][0]["relative_path"] == (
        "knowledge/health/aditya_birla_health/activ_one/documents/"
        "policy_wording_activ_one.txt"
    )
