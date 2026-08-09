from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_current import HEALTH_COVERAGE_REGISTRY

BINDING_PATH = Path("docs/architecture/ACTIV_ONE_NXT_POLICY_WORDING_SOURCE_BINDING.json")


def _binding() -> dict:
    return json.loads(BINDING_PATH.read_text(encoding="utf-8"))


def _activ_waiting_status() -> ConceptCoverageStatus:
    product = next(
        item
        for item in HEALTH_COVERAGE_REGISTRY.products
        if item.insurer_id == "aditya_birla_health"
    )
    concept = next(item for item in product.concepts if item.concept_id == "waiting_periods")
    return concept.status


def test_source_binding_targets_exact_approved_uin_and_variant() -> None:
    binding = _binding()
    assert binding["uin"] == "ADIHLIP24097V012324"
    assert binding["product_reference"] == "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324"
    assert binding["canonical_product_name"] == "Activ One NXT"


def test_source_binding_uses_registered_legal_authority_policy_wording() -> None:
    source = _binding()["source_registration"]
    assert source["document_id"] == "doc_d20a8488ecb3243f6de2"
    assert source["document_type"] == "policy_wording"
    assert source["evidence_role"] == "legal_authority"
    assert source["authority_score"] == 100
    assert source["document_hash_sha256"] == "e04bc4575d35e10bc86707ceeb839adf8a59f579bd27584c1b9000201bdac217"


def test_processed_asset_is_the_certified_factory_asset() -> None:
    asset = _binding()["certified_processed_asset"]
    assert asset["asset_id"] == "pdoc_72d03e57d4b49c68d69a11fc"
    assert asset["processing_quality_score"] == 98.0
    assert asset["processing_validation_status"] == "passed"
    assert asset["processing_warning_count"] == 0
    assert asset["processing_critical_warning_count"] == 0


def test_binding_requires_exact_identity_anchors() -> None:
    anchors = _binding()["exact_identity_anchors_in_processed_policy_wording"]
    assert "Product Name: Activ One, Product UIN: ADIHLIP24097V012324" in anchors
    assert "Activ One NXT" in anchors


def test_binding_preserves_waiting_period_review_gate() -> None:
    decision = _binding()["binding_decision"]
    assert decision["registered_policy_wording_may_be_used_for_waiting_period_candidate_isolation"] is True
    assert decision["waiting_period_candidate_review_required"] is True
    assert decision["waiting_period_fact_publication_allowed"] is False
    assert decision["coverage_registry_promotion_allowed"] is False


def test_activ_one_waiting_periods_remain_not_automated_after_source_binding() -> None:
    assert _activ_waiting_status() is ConceptCoverageStatus.NOT_AUTOMATED


def test_optional_waiting_period_reductions_are_not_base_publication_proof() -> None:
    notes = " ".join(_binding()["governance_notes"])
    assert "optional reduction" in notes.lower()
    assert "separate from base waiting-period mechanics" in notes
