# life_intelligence_lab — AMFI NAV Observation Adapter Prototype

## Purpose

An isolated reference prototype demonstrating a deterministic pipeline for
downloading, preserving, parsing and validating **AMFI mutual-fund NAV
data**, as a research proof-of-concept for PolicyScna's future Life
Intelligence dynamic-data layer (see `CLAUDE-LIFE-001`, `CLAUDE-LIFE-002`,
`CLAUDE-LIFE-003`).

```
AMFI source → raw immutable snapshot → source checksum → deterministic
parsing → row validation → canonical FundNAVObservation records →
output checksum → deterministic offline replay
```

## Experimental status

**This is prototype / research code. It is not production code.**

- It is fully isolated under `life_intelligence_lab/` and does not import
  from, modify, or depend on `factory_core/`, `insurance_intelligence/`,
  active Health knowledge, current orchestrators, or current production
  contracts.
- It has its own dependency declarations (`requirements.txt`,
  `requirements-dev.txt`), separate from any existing project dependency
  file.
- It covers **AMFI mutual-fund NAV data only** — no insurer ULIP data, no
  calculators, no fund comparison, no recommendations, no LLM, no
  database, no orchestration framework.
- Production readiness is explicitly **not** claimed — see
  `PROTOTYPE_REPORT.md` for known gaps and the recommended next action.

## Setup

No third-party runtime dependencies (standard library only). For running
tests:

```bash
pip install -r life_intelligence_lab/requirements-dev.txt
```

## Commands

Run all commands from the directory **containing** `life_intelligence_lab/`
(so it resolves as an importable package):

```bash
# 1. Download the AMFI NAV source into an immutable raw snapshot.
python -m life_intelligence_lab.scripts.download_amfi_nav
python -m life_intelligence_lab.scripts.download_amfi_nav --out-dir life_intelligence_lab/data/snapshots --timeout 30

# 2. Parse a saved snapshot into canonical FundNAVObservation records.
#    No network access is used or required.
python -m life_intelligence_lab.scripts.parse_amfi_nav --snapshot life_intelligence_lab/data/snapshots/<snapshot_id>

# 3. Offline deterministic replay: re-parse the same snapshot and prove
#    the output hash matches a prior run.
python -m life_intelligence_lab.scripts.replay_amfi_nav \
  --snapshot life_intelligence_lab/data/snapshots/<snapshot_id> \
  --compare-to life_intelligence_lab/data/canonical/<snapshot_id>
```

Run the test suite:

```bash
cd <parent of life_intelligence_lab/>
python -m pytest life_intelligence_lab/tests -v
```

## Outputs

Each run produces, under a snapshot- or run-specific directory:

| File | Content | Deterministic? |
|---|---|---|
| `manifest.json` | `RawSnapshot` metadata (source, retrieval time, hash, status) | Written once at download time |
| `raw.txt` | The exact, unmodified bytes retrieved from the source | Immutable once written |
| `observations.jsonl` | One canonical `FundNAVObservation` JSON record per line, sorted | **Yes** — byte-identical across repeated runs over the same snapshot |
| `rejected.jsonl` | One `RejectedRow` JSON record per line, per excluded row | **Yes** |
| `summary.json` | Accepted/rejected counts, rejection-reason breakdown, output hashes | **Yes** |
| `run_metadata.json` | Wall-clock time this particular run happened | **No** — deliberately isolated from the deterministic files above |

## Failure behaviour

Every failure mode fails **closed**, never silently:

- Download: HTTP error, timeout, or an empty response body all raise
  `DownloadFailedError` and persist a failure manifest for audit — no raw
  content is ever treated as valid just because *some* response arrived.
- Parsing: a malformed, invalid, or duplicate row is never dropped
  silently or guessed into shape — it is written to `rejected.jsonl` with
  a specific, stable reason code. The one exception is a genuinely
  *absent* optional ISIN (AMFI's own `-` convention), which is normal,
  not an error.
- Replay: loading a snapshot whose raw file's SHA-256 no longer matches
  its manifest raises a hash-mismatch error rather than silently parsing
  possibly-corrupted content.

## Limitations

See `PROTOTYPE_REPORT.md` for the full list, including: this sandbox's
network egress allowlist does not include `amfiindia.com`, so a live
download could not be exercised end-to-end here (the download path was
still tested via dependency injection and, separately, attempted live to
confirm and document the actual failure mode observed).

## Other prototypes in this sandbox

This directory also contains **LIFE-PROTOTYPE-002**, an isolated
deterministic Time Value of Money calculator runtime (Future Value,
Present Value, CAGR, Inflation-Adjusted Future Value), built as a
separate subpackage (`calculators/`) with no dependency on the AMFI
adapter code above. See `CALCULATOR_RUNTIME_README.md`,
`CALCULATOR_ARCHITECTURE.md`, and `PROTOTYPE_REPORT_002.md`.
