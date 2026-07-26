import json
import os

from life_intelligence_lab.canonical import write_canonical_outputs
from life_intelligence_lab.contracts import FUND_NAV_OBSERVATION_FIELD_ORDER
from life_intelligence_lab.parser import parse_amfi_nav


# --- 11. Deterministic output hash --------------------------------------------

def test_same_input_produces_identical_output_hash(valid_snapshot, valid_fixture_text, tmp_path):
    result_a = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    result_b = parse_amfi_nav(valid_fixture_text, valid_snapshot)

    hashes_a = write_canonical_outputs(result_a, str(tmp_path / "run_a"), run_label="a")
    hashes_b = write_canonical_outputs(result_b, str(tmp_path / "run_b"), run_label="b")

    assert hashes_a["observations_sha256"] == hashes_b["observations_sha256"]
    assert hashes_a["rejected_sha256"] == hashes_b["rejected_sha256"]

    # Byte-for-byte, not just hash-for-hash.
    with open(os.path.join(str(tmp_path / "run_a"), "observations.jsonl"), "rb") as fh:
        content_a = fh.read()
    with open(os.path.join(str(tmp_path / "run_b"), "observations.jsonl"), "rb") as fh:
        content_b = fh.read()
    assert content_a == content_b


def test_run_metadata_is_not_part_of_deterministic_hash(valid_snapshot, valid_fixture_text, tmp_path):
    import time

    result = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    hashes_a = write_canonical_outputs(result, str(tmp_path / "run_a"), run_label="a")
    time.sleep(0.01)  # ensure wall-clock run_timestamp would differ
    hashes_b = write_canonical_outputs(result, str(tmp_path / "run_b"), run_label="b")

    assert hashes_a["observations_sha256"] == hashes_b["observations_sha256"]

    with open(os.path.join(str(tmp_path / "run_a"), "run_metadata.json")) as fh:
        meta_a = json.load(fh)
    with open(os.path.join(str(tmp_path / "run_b"), "run_metadata.json")) as fh:
        meta_b = json.load(fh)
    assert meta_a["run_timestamp"] != meta_b["run_timestamp"]  # non-deterministic content isolated here


def test_canonical_record_field_order_is_stable(valid_snapshot, valid_fixture_text, tmp_path):
    result = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    write_canonical_outputs(result, str(tmp_path / "run"), run_label="order_check")
    with open(os.path.join(str(tmp_path / "run"), "observations.jsonl")) as fh:
        first_line = fh.readline()
    record = json.loads(first_line)
    assert list(record.keys()) == FUND_NAV_OBSERVATION_FIELD_ORDER


def test_nav_value_is_decimal_safe_string_not_float(valid_snapshot, valid_fixture_text, tmp_path):
    result = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    write_canonical_outputs(result, str(tmp_path / "run"), run_label="decimal_check")
    with open(os.path.join(str(tmp_path / "run"), "observations.jsonl")) as fh:
        records = [json.loads(line) for line in fh]
    target = next(r for r in records if r["amfi_scheme_code"] == "118551")
    assert isinstance(target["nav_value"], str)
    assert target["nav_value"] == "1234.5678"  # exact precision preserved, not float-rounded


def test_summary_counts_match_parse_result(errors_snapshot, errors_fixture_text, tmp_path):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    write_canonical_outputs(result, str(tmp_path / "run"), run_label="summary_check")
    with open(os.path.join(str(tmp_path / "run"), "summary.json")) as fh:
        summary = json.load(fh)
    assert summary["accepted_count"] == len(result.accepted)
    assert summary["rejected_count"] == len(result.rejected)
