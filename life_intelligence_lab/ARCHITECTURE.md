# Architecture Note — AMFI NAV Observation Adapter Prototype

## Why the downloader and parser are separate modules

`downloader.py` performs network I/O and file I/O; `parser.py` performs
pure, in-memory text transformation and never touches the network or the
filesystem for its source input. This split exists for three reasons:

1. **Testability without live network access.** Every parser test runs
   against an in-memory string. Every downloader test runs against an
   injected fake HTTP transport (`fetch_fn`). Neither module's tests can
   accidentally depend on AMFI actually being reachable.
2. **Separation of concerns matches separation of failure modes.**
   Network failures (timeout, HTTP error, empty response) are a
   fundamentally different category of problem from content failures
   (malformed row, invalid NAV, duplicate). Keeping them in different
   modules keeps their error handling — and their tests — from bleeding
   into each other.
3. **It mirrors the eventual production shape.** In `CLAUDE-LIFE-003`'s
   reference architecture, "dynamic data adapters" (fetch/normalize, no
   calculation) are explicitly a separate component from anything that
   interprets the data. This prototype's downloader/parser split is a
   small-scale rehearsal of that same boundary, one level down (fetch vs.
   parse, rather than adapter vs. calculator).

`test_downloader.py::test_downloader_module_does_not_import_parser`
enforces this boundary structurally, not just by convention.

## Why raw snapshots are immutable

A raw snapshot, once written, is never edited in place. Each snapshot
gets its own directory (`data/snapshots/<snapshot_id>/`) containing the
exact bytes retrieved (`raw.txt`) and a manifest recording that byte
content's SHA-256. `load_snapshot()` re-hashes the file on every read and
raises if it no longer matches — so any accidental or malicious
modification of a stored raw file is detected, not silently parsed.

This is the same lineage discipline `CLAUDE-LIFE-001` requires of the
production system: a raw artifact's hash is the anchor that makes
everything derived from it (parsed rows, canonical observations,
downstream calculations) independently verifiable back to an exact,
unmodified source.

## How observation date differs from retrieval date

Every `FundNAVObservation` carries two separate, purpose-built date/time
fields:

- `nav_valuation_date` — the date the NAV in the row is *for* (parsed
  from AMFI's own `DD-Mon-YYYY` date column, normalized to ISO-8601).
- `retrieval_timestamp` — the wall-clock time the *snapshot* containing
  that row was downloaded (inherited from the `RawSnapshot`, not
  regenerated at parse time).

These are never conflated. A NAV valued on a Friday but retrieved on the
following Monday (e.g., after a weekend) will show a `nav_valuation_date`
three days earlier than its `retrieval_timestamp` — exactly as it should.
This directly implements the instruction "do not assume retrieval date
equals NAV valuation date," and mirrors the same distinction
`CLAUDE-LIFE-001`'s dynamic-data contracts require for every observation
class, not just NAV.

## How deterministic replay works

Determinism has two enabling design choices:

1. **Deterministic, content-derived IDs.** `FundNAVObservation.observation_id`
   is a SHA-256-derived hash of `(scheme_code, nav_date, isin_payout)` —
   never a random UUID or a counter that depends on iteration order. Two
   parses of the same snapshot always produce the same observation IDs.
2. **Deterministic ordering and formatting.** Accepted observations are
   sorted by `(scheme_code, nav_date, isin_payout)` before serialization,
   regardless of the order rows appeared in the source file. JSON records
   use a fixed field order (declared once in `contracts.py`) and compact,
   stable separators. NAV values are serialized as `Decimal`-derived
   strings, never floats, so no floating-point representation drift can
   creep in between runs or platforms.

Everything that is genuinely non-deterministic — specifically, the
wall-clock time a parse or replay command happened to execute — is
written to a separate `run_metadata.json` file that is never read by
anything computing a hash. `observations.jsonl`, `rejected.jsonl`, and
`summary.json` are the deterministic content; `run_metadata.json` is the
one file allowed to vary between runs.

`scripts/replay_amfi_nav.py` proves this by re-parsing a saved snapshot
with **no network access whatsoever** (it does not import `urllib` or the
downloader's live fetch path at all — enforced by
`test_replay.py::test_replay_uses_no_network_module`) and comparing its
output hash against a prior run's `summary.json`.

## How this could later sit behind a PolicyScna adapter contract

This prototype's shapes are deliberately close to — but not the same as,
and not imported from — the contracts described in `CLAUDE-LIFE-001`
(`MarketObservation`/`FundNAVObservation`) and `CLAUDE-LIFE-003`
(`DynamicObservation`, the Observation Registry, the Identifier Resolver).
A future production adapter could reuse this prototype's structure as
follows:

- `RawSnapshot` → becomes the input contract to a governed **Observation
  Registry**'s ingestion path (LIFE-003 §3), rather than a local JSON
  manifest.
- `FundNAVObservation` → becomes (with the addition of a proper
  provenance envelope and `staleness_status`, per LIFE-003's information-
  class model) a real, registry-persisted `FundNAVObservation` record,
  queryable by scheme code rather than read from a flat file.
- The **Identifier Resolver** (LIFE-003 §3) would sit in front of this
  adapter's `amfi_scheme_code`/`isin_*` fields to prevent exactly the
  namespace-conflation risk LIFE-001/003 flag (SFIN ≠ AMFI scheme code ≠
  ISIN) — this prototype does not implement that resolver, since it only
  ever handles one namespace (AMFI).
- The **downloader/parser separation already matches** the eventual
  "dynamic data adapters do not calculate" boundary from LIFE-003 §3 —
  this prototype's parser does no arithmetic at all, not even a
  percentage change, consistent with that boundary.

None of this wiring exists in the prototype. It is deliberately scoped to
prove the deterministic pipeline in isolation first.
