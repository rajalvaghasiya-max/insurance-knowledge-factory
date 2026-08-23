import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_tata_copayment_is_knowledge_gap_not_manufactured_fact():
    data = _load("docs/architecture/tata_aig_medicare_premier_copayment_knowledge_gap_2026-08-23.json")
    assert data["repeatability_classification"]["classification"] == "KNOWLEDGE_GAP"
    assert data["repeatability_classification"]["representation_gap_observed"] is False
    assert data["repeatability_classification"]["architecture_failure_observed"] is False
    assert data["governance"]["certification_authorized"] is False
    assert set(data["forbidden_inferences"]) == {
        "copayment_is_0_percent",
        "copayment_does_not_apply",
        "product_has_no_copayment",
        "nearby_deductible_or_limit_values_are_copayment_values",
    }
    cis = data["reviewed_sources"][1]
    findings = {item["candidate_id"]: item for item in cis["candidate_findings"]}
    assert findings["candidate_page_4"]["candidate_text_sha256"] == "e03186077706214d8c08e6c63d0752018125e35baf7301d65adc428deff536f3"
    assert findings["candidate_page_7"]["candidate_text_sha256"] == "98126031088ce4bedc96f56ea93a0c4f6288e85f21205c86da1eb8758691859c"


def test_product4_result_follows_preregistered_inconclusive_rule():
    data = _load("docs/architecture/health_product4_repeatability_result_2026-08-23.json")
    assert data["protocol_baseline_commit"] == "bda5eb8721e04f8a78118ca4c4e054a09520a6d4"
    assert data["target_concepts"]["waiting_period"]["classification"] == "CONFIG_SPEC"
    assert data["target_concepts"]["copayment"]["classification"] == "KNOWLEDGE_GAP"
    assert data["primary_metrics"]["all_targets_pass"] is True
    assert data["protocol_outcome"]["classification"] == "REPEATABILITY_INCONCLUSIVE"
    assert data["protocol_outcome"]["repeatability_proven"] is False
    assert data["protocol_outcome"]["repeatability_failed"] is False
    assert data["protocol_outcome"]["architecture_rework_triggered"] is False
    assert data["governance"]["protocol_changed_after_product_observation"] is False
