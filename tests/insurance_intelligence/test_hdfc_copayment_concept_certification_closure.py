import json
from pathlib import Path

from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE


ROOT = Path(__file__).resolve().parents[2]
CLOSURE = ROOT / "docs/architecture/hdfc_ergo_optima_secure_v8_copayment_concept_certification_closure_2026-08-23.json"


def _copayment():
    return next(
        item for item in HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE.concepts
        if item.concept_id == "copayment"
    )


def test_hdfc_copayment_closure_preserves_definition_vs_operational_rule_boundary() -> None:
    data = json.loads(CLOSURE.read_text(encoding="utf-8"))
    by_candidate = {item["candidate_id"]: item for item in data["reviewed_occurrences"]}

    definition = by_candidate["candidate_page_3"]
    assert definition["candidate_text_sha256"] == "f8aeeccd32b501fc93b2bc699fcd04d43f239a1e40aacc8475c7152ea3f1d0e1"
    assert definition["classification"] == "DEFINITION_ONLY"
    assert definition["product_obligation_authorized"] is False

    operative = by_candidate["candidate_page_44"]
    assert operative["candidate_text_sha256"] == "66157d6b8ae478e7e46d0d40f19d00a87db7f949e14197b56bf08a5cf8cce743"
    assert operative["classification"] == "EXPLICIT_COPAYMENT_NONAPPLICATION_RULE"
    assert operative["live_certification_outcome"] == "PASS"
    assert operative["live_certification_completeness"] == "COMPLETE"
    assert operative["live_explanation_permitted"] is True


def test_hdfc_copayment_concept_is_certified_without_fabricating_percentage_or_readiness() -> None:
    data = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assessment = data["concept_assessment"]
    governance = data["governance"]

    assert assessment["current_base_wording_copayment_occurrences_reviewed"] is True
    assert assessment["positive_percentage_copayment_obligation_found"] is False
    assert assessment["definition_only_occurrence_excluded_from_product_truth"] is True
    assert assessment["operative_nonapplication_rule_certified"] is True
    assert assessment["zero_percent_obligation_manufactured"] is False
    assert assessment["concept_status"] == "CERTIFIED"

    assert governance["coverage_registry_promotion_authorized"] is True
    assert governance["publication_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False
    assert governance["customer_specific_cost_share_inference_authorized"] is False
    assert governance["claim_payment_inference_authorized"] is False

    copayment = _copayment()
    assert copayment.status is ConceptCoverageStatus.CERTIFIED
    assert copayment.comparison_ready is False
    assert copayment.decision_support_ready is False
    assert "docs/architecture/hdfc_ergo_optima_secure_v8_copayment_nonapplication_binding_spec.json" in copayment.evidence_reference_ids
    assert "docs/architecture/hdfc_ergo_optima_secure_v8_copayment_concept_certification_closure_2026-08-23.json" in copayment.evidence_reference_ids
    limitations = " ".join(copayment.limitations).lower()
    assert "definition-only" in limitations
    assert "does_not_apply" in limitations
    assert "0%" in limitations
    assert "positive copayment" in limitations
