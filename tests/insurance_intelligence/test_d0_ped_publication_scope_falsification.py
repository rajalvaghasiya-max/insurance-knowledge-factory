from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = (
    ROOT
    / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    / "ped_waiting_period_authoritative_publication.json"
)
CERTIFIED = (
    ROOT
    / "knowledge/factory/registry_backed/star_health_star_comprehensive/publication"
    / "ped_waiting_period_certified_evidence.json"
)


def test_ped_publication_projects_already_certified_subject_start_and_scope() -> None:
    publication = json.loads(PUBLICATION.read_text(encoding="utf-8"))
    certified = json.loads(CERTIFIED.read_text(encoding="utf-8"))

    published_ids = {
        item["component_id"]
        for item in publication["semantic_components"]
    }
    assert {
        "waiting_period_duration",
        "waiting_period_subject",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
    } <= published_ids

    certified_by_topic = {
        item["field_or_topic"]: item
        for item in certified["evidence_packages"]
    }
    assert (
        certified_by_topic["WAITING_PERIOD_SUBJECT"]["claim"]
        == "Waiting period applies to: pre_existing_disease_and_direct_complications."
    )
    assert (
        certified_by_topic["WAITING_PERIOD_START_BASIS"]["claim"]
        == "The waiting period start basis is INSURED_PERSON_FIRST_COVERAGE."
    )
    assert (
        certified_by_topic["APPLICABILITY_SCOPE"]["claim"]
        == (
            "Waiting-period applicability: scope_type=POLICY_WIDE; "
            "sum_insured_enhancement_effect=REAPPLIES_TO_ENHANCED_PORTION."
        )
    )
