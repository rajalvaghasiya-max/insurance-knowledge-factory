# Prototype Report — LIFE-PROTOTYPE-001: AMFI NAV Observation Adapter

**Status: PROTOTYPE. NOT PRODUCTION READY. NOT CLAIMED TO BE.**

## 1. Prototype status

Complete and passing. All required components (downloader, raw-snapshot
contract, parser, `FundNAVObservation` contract, validation, canonical
output, offline replay) are implemented, isolated under
`life_intelligence_lab/`, and independently tested. The full pipeline was
exercised end-to-end via the actual CLI scripts (not just unit tests),
including one **real** network attempt against the live AMFI URL (see §9).

## 2. Directory created

`life_intelligence_lab/` (did not previously exist; created fresh at the
repository root, sibling to — not inside — any existing production
directories).

## 3. Files changed

All files below are **new**; nothing outside `life_intelligence_lab/` was
touched, read from, or imported.

```
life_intelligence_lab/
├── __init__.py
├── contracts.py            # RawSnapshot, RejectedRow, FundNAVObservation
├── validation.py           # scheme code / NAV / date / name / ISIN validators
├── parser.py                # AMFI flat-file parser (no network)
├── downloader.py             # AMFI source fetch + immutable snapshot writer
├── canonical.py              # deterministic JSONL writer + hashing
├── requirements.txt          # runtime deps (none beyond stdlib)
├── requirements-dev.txt      # test deps (pytest only)
├── README.md
├── ARCHITECTURE.md
├── PROTOTYPE_REPORT.md        # this file
├── scripts/
│   ├── __init__.py
│   ├── download_amfi_nav.py
│   ├── parse_amfi_nav.py
│   └── replay_amfi_nav.py
├── fixtures/
│   ├── sample_amfi_nav_valid.txt
│   └── sample_amfi_nav_with_errors.txt
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_validation.py
│   ├── test_parser.py
│   ├── test_downloader.py
│   ├── test_canonical.py
│   └── test_replay.py
└── data/                      # run artifacts (snapshots + canonical output)
    ├── snapshots/
    │   ├── demo_snapshot_001/            (successful offline-simulated download)
    │   └── snap_2026-07-26T130638.../     (real, live, failed 403 attempt — kept as evidence, see §9)
    ├── canonical/demo_snapshot_001/
    └── canonical_replay/demo_snapshot_001/
```

## 4. Dependencies added inside the sandbox

- **Runtime:** none beyond the Python standard library (`urllib`,
  `hashlib`, `json`, `decimal`, `dataclasses`, `re`, `datetime`, `os`).
- **Test-only:** `pytest>=7.0,<9.0` (declared in `requirements-dev.txt`;
  installed in this sandbox at `pytest 9.1.1`, which satisfies the
  declared range at its upper edge — noted for the record).

Nothing was added to any existing/production dependency file.

## 5. Commands to run

```bash
cd <parent of life_intelligence_lab/>

python -m life_intelligence_lab.scripts.download_amfi_nav
python -m life_intelligence_lab.scripts.parse_amfi_nav --snapshot life_intelligence_lab/data/snapshots/<snapshot_id>
python -m life_intelligence_lab.scripts.replay_amfi_nav --snapshot life_intelligence_lab/data/snapshots/<snapshot_id> --compare-to life_intelligence_lab/data/canonical/<snapshot_id>

python -m pytest life_intelligence_lab/tests -v
```

## 6. Tests executed

`python -m pytest life_intelligence_lab/tests -v`, run from `/home/claude`.

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
collected 45 items

test_canonical.py::test_same_input_produces_identical_output_hash PASSED
test_canonical.py::test_run_metadata_is_not_part_of_deterministic_hash PASSED
test_canonical.py::test_canonical_record_field_order_is_stable PASSED
test_canonical.py::test_nav_value_is_decimal_safe_string_not_float PASSED
test_canonical.py::test_summary_counts_match_parse_result PASSED
test_downloader.py::test_successful_download_writes_snapshot_and_hash PASSED
test_downloader.py::test_http_error_raises_and_writes_failure_manifest PASSED
test_downloader.py::test_timeout_raises_and_is_distinguished_from_http_error PASSED
test_downloader.py::test_empty_response_is_rejected_not_treated_as_valid PASSED
test_downloader.py::test_load_snapshot_roundtrips_and_verifies_hash PASSED
test_downloader.py::test_load_snapshot_detects_hash_mismatch PASSED
test_downloader.py::test_downloader_module_does_not_import_parser PASSED
test_downloader.py::test_downloader_does_not_parse_nav_rows PASSED
test_parser.py::test_valid_row_parses_to_observation PASSED
test_parser.py::test_missing_optional_isin_does_not_reject_row PASSED
test_parser.py::test_invalid_scheme_code_is_rejected PASSED
test_parser.py::test_invalid_nav_format_is_rejected PASSED
test_parser.py::test_zero_and_negative_nav_are_rejected PASSED
test_parser.py::test_invalid_date_is_rejected PASSED
test_parser.py::test_empty_source_yields_no_observations PASSED
test_parser.py::test_duplicate_row_is_rejected_not_double_counted PASSED
test_parser.py::test_section_heading_attached_to_rows PASSED
test_parser.py::test_accepted_observations_are_deterministically_ordered PASSED
test_parser.py::test_missing_scheme_name_is_rejected PASSED
test_parser.py::test_malformed_row_too_few_fields_is_rejected PASSED
test_parser.py::test_malformed_isin_produces_warning_not_rejection PASSED
test_parser.py::test_parser_never_touches_network_or_filesystem_for_source PASSED
test_replay.py::test_replay_cli_matches_original_parse_cli_hash PASSED
test_replay.py::test_replay_cli_fails_closed_on_missing_snapshot PASSED
test_replay.py::test_replay_uses_no_network_module PASSED
test_validation.py::test_validate_scheme_code_valid PASSED
test_validation.py::test_validate_scheme_code_invalid PASSED
test_validation.py::test_validate_scheme_code_empty PASSED
test_validation.py::test_validate_nav_valid_preserves_precision PASSED
test_validation.py::test_validate_nav_zero_rejected PASSED
test_validation.py::test_validate_nav_negative_rejected PASSED
test_validation.py::test_validate_nav_non_numeric_rejected PASSED
test_validation.py::test_validate_nav_date_valid PASSED
test_validation.py::test_validate_nav_date_invalid_format PASSED
test_validation.py::test_validate_scheme_name_valid PASSED
test_validation.py::test_validate_scheme_name_empty_rejected PASSED
test_validation.py::test_normalize_isin_dash_is_absent_no_warning PASSED
test_validation.py::test_normalize_isin_empty_is_absent_no_warning PASSED
test_validation.py::test_normalize_isin_valid_shape PASSED
test_validation.py::test_normalize_isin_malformed_becomes_none_with_warning PASSED

============================== 45 passed in 0.08s ===============================
```

## 7. Test counts

**45 tests, 45 passed, 0 failed, 0 skipped.** Covers all 15 required cases
from the assignment (valid row; missing optional ISIN; invalid scheme
code; invalid NAV; zero/negative NAV; invalid date; empty source;
duplicate row; section/category parsing; deterministic ordering;
deterministic output hash; downloader/parser separation; HTTP failure;
timeout handling; offline replay) plus 4 additional cases found useful
during implementation (missing scheme name; malformed short row; a
present-but-malformed ISIN warned-not-rejected; snapshot hash-mismatch
detection on tamper).

## 8. Sample accepted observation

Captured verbatim from an actual pipeline run (`demo_snapshot_001`):

```json
{
    "observation_id": "obs_0b2392fb8405d689a57b650f",
    "observation_type": "mutual_fund_nav",
    "amfi_scheme_code": "118551",
    "isin_payout_growth": "INF209K01UN8",
    "isin_reinvestment": null,
    "scheme_name": "Axis Overnight Fund - Regular Plan - Growth",
    "category": "Open Ended Schemes(Overnight Fund)",
    "nav_value": "1234.5678",
    "currency": "INR",
    "nav_valuation_date": "2026-07-25",
    "retrieval_timestamp": "2026-07-26T13:06:30.012207+00:00",
    "source_snapshot_id": "demo_snapshot_001",
    "source_sha256": "40e8f52208058aba9405e6ba43d5b5402cd8e033b0a8e380b2f49c1756590ba3",
    "adapter_version": "amfi-nav-adapter/0.1.0",
    "parser_version": "amfi-nav-parser/0.1.0",
    "validation_status": "accepted",
    "warnings": []
}
```

Note `nav_valuation_date` (2026-07-25) is structurally distinct from
`retrieval_timestamp` (2026-07-26T13:06:30Z) — captured, not collapsed,
per the assignment's explicit instruction.

## 9. Sample rejected row

```json
{
    "line_number": 12,
    "raw_line": "ABCDE;INF109K01235;-;Bad Scheme Code Fund;1000.0000;25-Jul-2026",
    "section": "Open Ended Schemes(Liquid Fund)",
    "reason": "invalid_scheme_code",
    "source_snapshot_id": "demo_snapshot_001"
}
```

Full breakdown from the same run (5 accepted, 8 rejected, from the
deliberately error-laden fixture):

```json
{
  "accepted_count": 5,
  "rejected_count": 8,
  "rejected_by_reason": {
    "duplicate_row: same scheme_code/nav_date/isin as line 11": 1,
    "invalid_nav_date": 1,
    "invalid_nav_format": 1,
    "invalid_scheme_code": 1,
    "malformed_row: expected at least 6 semicolon-delimited fields, got 4": 1,
    "missing_scheme_name": 1,
    "nav_not_positive": 2
  }
}
```

## 10. Raw snapshot hash

`raw_sha256 = 40e8f52208058aba9405e6ba43d5b5402cd8e033b0a8e380b2f49c1756590ba3`
(SHA-256 of the fixture content used to simulate the AMFI response for
`demo_snapshot_001`, verified byte-for-byte on load).

## 11. Canonical output hash

```
observations_sha256 = 7c93b14ace78a0a46ae8d9eb1ebd0e9499d7253241e6c204826a3abe0d9a3def
rejected_sha256      = 031050f3fb39ce63f14173256a5e53b94bb65dbef05c14a6d618575b5b1dba14
```

## 12. Deterministic replay result

Ran `replay_amfi_nav.py` against `demo_snapshot_001` with `--compare-to`
pointing at the original parse's output directory:

```
Replay complete (offline, no network access used).
  snapshot_id: demo_snapshot_001
  observations_sha256: 7c93b14ace78a0a46ae8d9eb1ebd0e9499d7253241e6c204826a3abe0d9a3def
  rejected_sha256: 031050f3fb39ce63f14173256a5e53b94bb65dbef05c14a6d618575b5b1dba14
  DETERMINISTIC REPLAY: MATCH (hashes identical to prior run)
```

Exit code 0. Hashes are byte-identical to the original parse run
(verified both via hash comparison and, in the test suite, via direct
byte-content comparison of the two `observations.jsonl` files).

**A note on honesty about network access from this sandbox:** the real
`download_amfi_nav.py` CLI was also run once against the live AMFI URL
(`https://www.amfiindia.com/spages/NAVAll.txt`) to confirm actual
behaviour rather than only asserting it. It received an **HTTP 403**
(consistent with this sandbox's network egress allowlist not including
`amfiindia.com`), and the downloader correctly raised
`DownloadFailedError`, wrote a failure manifest for audit
(`data/snapshots/snap_2026-07-26T130638.../manifest.json`, retained as
evidence), and persisted no raw content — exit code 1, no false success.
All other end-to-end demonstrations in this report (successful download,
parse, replay) use the injectable `fetch_fn` with the checked-in fixture
content standing in for a live AMFI response, exactly as the automated
test suite does.

## 13. Known limitations

- **Live AMFI download not exercisable end-to-end in this sandbox**, for
  the network-allowlist reason above. The downloader's HTTP logic is
  otherwise fully implemented (real `urllib`-based transport) and its
  behaviour (success, HTTP error, timeout, empty response) is fully unit
  -tested via dependency injection — but a genuinely successful live
  fetch has not been observed by this prototype run.
- **Scheme-code and ISIN validation are shape checks, not authority
  checks.** The prototype confirms a scheme code is numeric and an ISIN
  is 12 alphanumeric characters; it does not verify either against
  AMFI's or a depository's actual registry of valid codes. A well-formed
  but nonexistent scheme code would currently be accepted.
- **No handling of AMFI-specific edge cases not present in the fixtures**
  — e.g. schemes suspended/under NAV freeze, or format variations AMFI
  has historically introduced without notice. The fixtures were
  hand-constructed to match the documented format from `CLAUDE-LIFE-001`,
  not captured from a live response (see limitation above).
- **No retry/backoff logic** on transient HTTP failures — a single
  attempt either succeeds or fails closed.
- **Single-file scope**: this prototype does not address ULIP NAV data
  (explicitly out of scope per the assignment), nor does it implement the
  Identifier Resolver, Observation Registry, or any of the
  `CLAUDE-LIFE-003` components it is designed to eventually sit behind.

## 14. Licence / reuse considerations

- AMFI's daily NAV flat file is a long-standing, widely-mirrored public
  convention (per `CLAUDE-LIFE-001` §2.C) rather than a contractually
  licensed feed with a published API terms-of-service page found during
  that research. This prototype does not redistribute AMFI data anywhere
  outside its own local run artifacts; any future production use should
  independently re-confirm current reuse terms directly from
  `amfiindia.com`, since this observation is unchanged evidence from
  `CLAUDE-LIFE-001`'s research pass and could be stale by the time this
  prototype is revisited.
- This prototype's own code uses only the Python standard library, so it
  introduces no new third-party licence obligations.

## 15. Recommendation

**Retain as reference.**

The deterministic pipeline (immutable snapshot → checksum → deterministic
parse → explicit validation → canonical, hash-verified output → proven
offline replay) works as designed and is fully tested. It is a sound
starting shape for a real AMFI adapter once wired behind the governed
Observation Registry and Identifier Resolver described in
`CLAUDE-LIFE-003`. It should **not** be promoted toward production as-is:
the scheme-code/ISIN shape-only validation and the untested live-fetch
path (§13) both need attention first, and none of the surrounding
governance (registry, resolver, staleness policy enforcement beyond a
single field) exists yet outside this prototype's own boundary.
