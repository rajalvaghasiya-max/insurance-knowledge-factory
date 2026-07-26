# Deterministic TVM Calculator Runtime — Prototype README

**Prototype status: `EXPERIMENTAL`.** May be reclassified only after tests
and review.

## Purpose

An isolated deterministic Time Value of Money (TVM) calculator runtime,
demonstrating:

```
CalculationRequest → calculator registry lookup → input normalization →
deterministic calculation → CalculationTrace → CalculationResult →
validation → input/output hashes → deterministic replay
```

for PolicyScna's future Life Intelligence calculator layer (see
`CLAUDE-LIFE-002`, `CLAUDE-LIFE-003`). Built inside the same
`life_intelligence_lab/` sandbox as `LIFE-PROTOTYPE-001` (the AMFI NAV
adapter), but as a fully separate subpackage (`life_intelligence_lab/calculators/`)
with **no dependency on anything AMFI-specific**.

## Experimental status

**This is experimental reference code. It is not production code.**

- Isolated under `life_intelligence_lab/calculators/`, `scripts/run_calculator.py`,
  `scripts/replay_calculation.py`, and `tests/test_calculators/`.
- Does not import from, modify, or depend on `factory_core/`,
  `insurance_intelligence/`, active Health knowledge, current production
  contracts, or existing Health orchestration.
- Does not import from `life_intelligence_lab.downloader`, `.parser`, or
  the root-level `.contracts`/`.canonical` modules built by
  LIFE-PROTOTYPE-001 — see `CALCULATOR_ARCHITECTURE.md` for why.
- Uses only the Python standard library at runtime.

## Supported calculators

| Calculator ID | Version | Formula | Status |
|---|---|---|---|
| `FV_LUMP_SUM` | 1 | `FV = PV × (1+r)^n` | active |
| `FV_LUMP_SUM` | 0 | (same, deliberately retired) | **retired** — kept only to exercise the retirement path |
| `PV_LUMP_SUM` | 1 | `PV = FV ÷ (1+r)^n` | active |
| `CAGR` | 1 | `CAGR = (ending÷beginning)^(1/n) − 1` | active |
| `INFLATION_ADJUSTED_FV` | 1 | Exact Fisher relationship; caller selects method `deflate_nominal` or `exact_real_rate` | active |
| `INFLATION_ADJUSTED_FV_APPROX` | 1 | `nominal − inflation` shortcut — a **separate, separately-warned** calculator, never a hidden mode of the exact one | active |

No other calculator families (XIRR, SIP, HLV, tax, product-specific
insurance calculations, recommendations) exist anywhere in this
prototype.

## Setup

No third-party runtime dependencies. For tests: `pip install -r life_intelligence_lab/requirements-dev.txt` (shared with LIFE-PROTOTYPE-001; still pytest only).

## Commands

Run from the directory **containing** `life_intelligence_lab/`:

```bash
# Run a request against a registered calculator (--calculator/--version
# are a sanity check against the request file's own declared calculator).
python -m life_intelligence_lab.scripts.run_calculator \
  --calculator FV_LUMP_SUM --version 1 \
  --input life_intelligence_lab/examples/fv_request.json

# Deterministically replay the same request offline and compare hashes
# against a prior run's output.
python -m life_intelligence_lab.scripts.replay_calculation \
  --request life_intelligence_lab/examples/fv_request.json \
  --compare-to life_intelligence_lab/data/calculations/example_fv_100000_8pct_10y
```

Run the tests:

```bash
python -m pytest life_intelligence_lab/tests/test_calculators -v
```

## Input conventions

- **Numbers as strings.** `input_values` should give decimal-looking
  numbers as JSON strings (e.g. `"100000"`, `"0.08"`), not bare JSON
  numbers. Integers are also accepted (exact). **Bare JSON floats are
  rejected** — precision cannot be guaranteed once a value has passed
  through IEEE-754, so the runtime refuses to accept one at all rather
  than accept a value it cannot promise decimal-safety for.
- **Rates must declare their unit.** Every rate-like field
  (`periodic_rate`, `nominal_rate`, `inflation_rate`) must have a
  matching entry in `input_units` set to exactly `"decimal"` or
  `"percentage"`. There is no default and no magnitude-based guessing —
  a bare `"8"` with no declared unit is rejected, not interpreted as
  either 8% or 800%.
- **Currency is required for money-producing calculators**, validated
  against a small supported whitelist (`INR`, `USD`, `GBP`, `EUR`), and
  is a top-level request field (not part of `input_values`).
- **Method/convention selection has no default where multiple exist.**
  `INFLATION_ADJUSTED_FV` requires an explicit `"method"` field — the
  request is rejected, not defaulted, if it's missing or unrecognized.

## Output contracts

Every executed request produces a `CalculationResult` and, if and only
if `status == "SUCCESS"`, an accompanying `CalculationTrace`. Both are
written as `result.json` / `trace.json` under an output directory, plus
a separate `run_metadata.json` holding only the wall-clock time of that
particular CLI invocation — never mixed into the deterministic content.

- `result.json` — status, output values (rounded), warnings,
  limitations, the trace id it's tied to, and two hashes
  (`deterministic_input_hash`, `deterministic_output_hash`).
- `trace.json` — every normalized input, every calculation step with its
  substituted expression and full-precision unrounded value, the
  rounding actually applied, and the same two hashes plus enough context
  (`calculation_date`, `currency`, `method`) to let anyone independently
  recompute them from the trace alone.

## Failure behaviour

Every non-`SUCCESS` result carries **no output values, no output hash,
and no trace** — a failure never includes a plausible-looking number.
Five closed statuses:

| Status | Meaning | Example |
|---|---|---|
| `SUCCESS` | Computed and validated | — |
| `INVALID_INPUT` | Malformed, missing, ambiguous, or incompatible input | negative periods, unitless rate, `NaN` |
| `FAILED_CLOSED` | Well-formed input, but mathematically undefined for this formula | CAGR with a zero beginning value |
| `UNSUPPORTED_CALCULATOR` | Unknown id, unknown version, or a retired calculator | requesting `FV_LUMP_SUM:v0` |
| `VALIDATION_FAILED` | Post-hoc consistency check failed (tampering / corruption) | a mutated hash caught by `validate_result` |

## Limitations

See `PROTOTYPE_REPORT_002.md` for the full list — in short: only four
calculator families exist; scheme/product-specific insurance logic,
XIRR/SIP/HLV, tax rules, market-data fetching, and any form of
recommendation or product comparison are all explicitly out of scope for
this prototype and not present anywhere in the code.
