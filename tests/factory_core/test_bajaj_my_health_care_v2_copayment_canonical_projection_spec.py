from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SPEC = (
    REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "bajaj_my_health_care_v2_copayment_canonical_projection_spec.json"
)


def _load() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_projection_uses_generic_contract_and_v2_binding() -> None:
    spec = _load()

    assert spec["projection_type"] == "generic_legal_condition_canonical_projection_v1"
    assert spec["reviewed_by_human"] is True
    assert spec["binding_manifest_path"].endswith(
        "/v2/generic_legal_condition_binding/bajaj_my_health_care_v2_copayment_binding.json"
    )
    assert spec["classification_manifest_path"].endswith(
        "/v2/governance/bajaj_my_health_care_v2_document_classification.json"
    )


def test_projection_context_is_bound_to_current_bajaj_identity() -> None:
    context = _load()["product_context"]

    assert context["insurer_id"] == "bajaj_allianz_general"
    assert context["insurer_legal_name"] == "Bajaj General Insurance Limited"
    assert context["product_id"] == "my_health_care"
    assert context["product_name"] == "My Health Care Plan"
    assert context["domain"] == "health"
    assert context["product_uin"] == "BAJHLIP26074V022526"
    assert context["product_version_id"] == (
        "pv_bajaj_allianz_general_my_health_care_bajhlip26074v022526"
    )


def test_projection_stage_does_not_grant_publication_authority() -> None:
    spec = _load()

    forbidden_top_level_keys = {
        "publication_status",
        "publication_decision",
        "authoritative_publication",
        "customer_entitlement",
    }
    assert forbidden_top_level_keys.isdisjoint(spec)
