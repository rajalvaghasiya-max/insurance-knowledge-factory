from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.canonical.waiting_period_material_rules_binding import (
    WaitingPeriodMaterialRulesBinding,
    WaitingPeriodMaterialRulesBindingError,
)


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "source.pdf").write_bytes(b"source")
    (tmp_path / "registration.json").write_text(json.dumps({
        "document": {"document_id": "doc", "document_version_id": "doc:v1", "storage_locator": "source.pdf", "content_sha256": "d" * 64, "document_type": "policy_wording"},
        "evidence_review": {"candidates": [{"candidate_id": "candidate_page_1", "source_page": 1, "source_char_range": {"start": 0, "end": 10}, "text_sha256": "a" * 64, "excerpt": "24 months; accident exception; longer of PED applies."}]},
    }), encoding="utf-8")
    (tmp_path / "bundle.json").write_text(json.dumps({
        "registration_type": "generic_source_registration_bundle_v1",
        "product_context": {"source_scope": "reusable_generic", "insurer_id": "i", "product_id": "p", "product_display_name": "P"},
        "sources": [{"document_id": "doc", "authority_role": "primary_legal", "registration_output_path": "registration.json"}],
    }), encoding="utf-8")
    (tmp_path / "base.json").write_text(json.dumps({
        "schema_version": "1.0", "binding_type": "waiting_period_binding_v1", "binding_id": "base", "reviewed_by_human": True,
        "generic_source_bundle_path": "bundle.json",
        "evidence_selections": [{"role": "mechanism", "document_id": "doc", "candidate_id": "candidate_page_1", "candidate_text_sha256": "a" * 64}],
        "mechanic": {"waiting_period_type": "SPECIFIC_DISEASE_PROCEDURE", "duration_value": 24, "duration_unit": "MONTHS", "start_basis": "INSURED_PERSON_FIRST_COVERAGE", "applies_to": ["listed_conditions"], "exclusions_or_exceptions": ["accident"], "modifications": [], "schedule_dependency": None, "continuity_dependency": "prior coverage credit", "scope_type": "POLICY_WIDE", "scope_reference": None, "value_source": "PRODUCT_FIXED", "member_waiting_basis": None, "sum_insured_enhancement_effect": "REAPPLIES_TO_ENHANCED_PORTION"},
    }), encoding="utf-8")
    spec = tmp_path / "rules.json"
    spec.write_text(json.dumps({
        "schema_version": "1.0", "binding_type": "waiting_period_material_rules_binding_v1", "binding_id": "rules", "reviewed_by_human": True, "base_binding_spec_path": "base.json",
        "material_rules": [
            {"rule_id": "longer", "rule_type": "RELATIONSHIP_LONGER_OF", "statement": "longer applies", "related_waiting_period_type": "PRE_EXISTING_DISEASE", "evidence_candidate_ids": ["candidate_page_1"]},
            {"rule_id": "applies", "rule_type": "APPLICABILITY_CONDITION", "statement": "applies after inception", "related_waiting_period_type": None, "evidence_candidate_ids": ["candidate_page_1"]},
        ],
    }), encoding="utf-8")
    return spec


def test_binds_material_rules_to_already_bound_exact_candidate(tmp_path: Path) -> None:
    result = WaitingPeriodMaterialRulesBinding().bind_from_spec_file(spec_path=_fixture(tmp_path), repository_root=tmp_path, bound_at="2026-08-22T00:00:00+00:00")
    assert result.manifest["material_rules_status"] == "reviewed_material_rules_bound_not_published"
    assert [item["rule_type"] for item in result.manifest["material_rules"]] == ["RELATIONSHIP_LONGER_OF", "APPLICABILITY_CONDITION"]
    assert result.manifest["resolution_status"] == "resolved_from_mechanism_evidence"
    assert result.manifest["publication_status"] == "bound_not_published"


def test_fails_closed_when_material_rule_references_unbound_candidate(tmp_path: Path) -> None:
    spec_path = _fixture(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["material_rules"][0]["evidence_candidate_ids"] = ["candidate_page_2"]
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(WaitingPeriodMaterialRulesBindingError, match="unbound candidate"):
        WaitingPeriodMaterialRulesBinding().bind_from_spec_file(spec_path=spec_path, repository_root=tmp_path)
