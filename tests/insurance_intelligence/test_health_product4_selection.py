import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SELECTION = ROOT / "docs/architecture/health_product4_selection_tata_aig_medicare_premier_2026-08-23.json"
PROTOCOL = ROOT / "docs/architecture/health_product4_repeatability_test_protocol_v1.json"
BASELINE = "bda5eb8721e04f8a78118ca4c4e054a09520a6d4"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_product4_selection_occurs_after_preregistered_protocol() -> None:
    selection = _load(SELECTION)
    protocol = _load(PROTOCOL)
    assert selection["selected_after_protocol_preregistration"] is True
    assert selection["repeatability_baseline_commit"] == BASELINE
    assert protocol["baseline"]["commit_sha"] == BASELINE
    assert protocol["experiment"]["product_selected_at_preregistration"] is False


def test_tata_aig_medicare_premier_is_locked_as_product4() -> None:
    selected = _load(SELECTION)["selected_product"]
    assert selected == {
        "insurer_id": "tata_aig_general",
        "product_id": "medicare_premier",
        "canonical_product_name": "TATA AIG MediCare Premier",
        "uin": "TATHLIP26052V052526",
        "product_reference": "tata_aig_general:medicare_premier:TATHLIP26052V052526",
    }


def test_selection_does_not_relax_repeatability_freeze() -> None:
    boundaries = _load(SELECTION)["experiment_boundaries"]
    assert boundaries["target_concepts"] == ["copayment", "waiting_period"]
    assert boundaries["generic_runtime_remains_frozen"] is True
    assert boundaries["semantic_fit_not_assessed_before_selection"] is True
    assert boundaries["runtime_extension_before_initial_scoring_authorized"] is False
    assert boundaries["decision_logic_in_config_authorized"] is False


def test_source_identity_is_locked_before_semantic_inventory() -> None:
    source = _load(SELECTION)["authoritative_source_checkpoint"]
    assert source["uin_observed_in_policy_wording"] == "TATHLIP26052V052526"
    assert source["policy_wording_page_count_observed"] == 60
    assert source["source_acquisition_not_yet_registered"] is True
