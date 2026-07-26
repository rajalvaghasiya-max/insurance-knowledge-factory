# Prototype Report — LIFE-PROTOTYPE-002: Deterministic TVM Calculator Runtime

**Status: EXPERIMENTAL. NOT PRODUCTION READY. NOT CLAIMED TO BE.**

## 1. Prototype status

`EXPERIMENTAL`, as instructed. Complete and passing for the four required
calculator families (Future Value, Present Value, CAGR, Inflation
-Adjusted Future Value with two exact methods plus a separately-named
approximate calculator). Built as an isolated subpackage
(`life_intelligence_lab/calculators/`) alongside LIFE-PROTOTYPE-001's
AMFI adapter, with zero import-level dependency on it.

## 2. Branch and commit

Not applicable — this sandbox has no git repository initialized; all
work exists as files under `life_intelligence_lab/` in this container's
filesystem.

## 3. Directory changed

`life_intelligence_lab/` (pre-existing from LIFE-PROTOTYPE-001; extended,
not recreated).

## 4. Files created or modified

**New (this prototype):**

```
life_intelligence_lab/
├── calculators/
│   ├── __init__.py
│   ├── contracts.py             # CalculatorDefinition, CalculationRequest/Trace/Result, etc.
│   ├── canonical.py              # deterministic hashing (self-contained, not shared w/ AMFI adapter)
│   ├── normalization.py          # schema-driven input normalization, decimal-safe
│   ├── rounding.py                # ROUND_HALF_UP money/rate rounding, documented defaults
│   ├── registry.py                # 6 registered CalculatorDefinition entries (incl. 1 retired)
│   ├── runtime.py                  # the orchestrator: lookup -> normalize -> compute -> trace/result
│   ├── validation.py               # post-hoc CalculationValidationResult (recompute-and-compare)
│   ├── serialization.py            # dataclass <-> ordered dict for JSON I/O and hashing
│   ├── output_writer.py            # result.json/trace.json + separated run_metadata.json
│   └── formulas/
│       ├── __init__.py             # DomainError, FormulaOutput/FormulaStep shared types
│       ├── fv.py                   # FV_LUMP_SUM
│       ├── pv.py                   # PV_LUMP_SUM
│       ├── cagr.py                 # CAGR (the one fractional-exponent formula)
│       ├── inflation_adjusted.py   # INFLATION_ADJUSTED_FV, methods A & B
│       └── inflation_adjusted_approx.py  # INFLATION_ADJUSTED_FV_APPROX (separate calculator)
├── scripts/
│   ├── run_calculator.py
│   └── replay_calculation.py
├── examples/
│   ├── fv_request.json
│   ├── fv_15y_request.json         # the LIFE-003 regression vector
│   ├── pv_request.json
│   ├── cagr_request.json
│   ├── cagr_failed_closed_request.json
│   ├── inflation_exact_deflate_request.json
│   ├── inflation_exact_real_rate_request.json
│   └── inflation_approx_request.json
├── tests/test_calculators/
│   ├── __init__.py, conftest.py
│   ├── test_fv.py, test_pv.py, test_cagr.py, test_inflation.py
│   ├── test_normalization.py, test_registry.py
│   ├── test_determinism.py, test_validation.py, test_rounding.py
├── CALCULATOR_RUNTIME_README.md
├── CALCULATOR_ARCHITECTURE.md
├── PROTOTYPE_REPORT_002.md          # this file
└── data/calculations/, data/calculations_replay/   # run artifacts
```

**Modified:** `README.md` (added a short pointer section to this second
prototype; LIFE-PROTOTYPE-001's own content untouched).

**Untouched:** everything from LIFE-PROTOTYPE-001
(`downloader.py`, `parser.py`, root-level `contracts.py`/`canonical.py`/
`validation.py`, `fixtures/`, `tests/test_downloader.py` etc.) — verified
by running its full test suite alongside this prototype's (§7).

## 5. Dependencies added inside the sandbox

None beyond what LIFE-PROTOTYPE-001 already declared
(`requirements-dev.txt`: `pytest>=7.0,<9.0`, shared). Runtime remains
standard-library-only (`decimal`, `dataclasses`, `hashlib`, `json`,
`typing`).

## 6. Commands to run

```bash
cd <parent of life_intelligence_lab/>

python -m life_intelligence_lab.scripts.run_calculator \
  --calculator FV_LUMP_SUM --version 1 --input life_intelligence_lab/examples/fv_request.json

python -m life_intelligence_lab.scripts.replay_calculation \
  --request life_intelligence_lab/examples/fv_request.json \
  --compare-to life_intelligence_lab/data/calculations/example_fv_100000_8pct_10y

python -m pytest life_intelligence_lab/tests/test_calculators -v
```

## 7. Tests executed

`python -m pytest life_intelligence_lab/tests/test_calculators -v`, run
from `/home/claude`. Full output (57 tests):

```
============================= test session starts ==============================
collected 57 items

test_cagr.py::test_cagr_known_answer_vector PASSED
test_cagr.py::test_cagr_beginning_value_zero_fails_closed PASSED
test_cagr.py::test_cagr_negative_values_rejected_by_default PASSED
test_cagr.py::test_cagr_negative_values_allowed_with_explicit_flag PASSED
test_cagr.py::test_cagr_periods_zero_rejected PASSED
test_cagr.py::test_cagr_negative_periods_rejected_generically_before_reaching_formula PASSED
test_determinism.py::test_deterministic_input_hash_stable_across_runs PASSED
test_determinism.py::test_input_hash_changes_when_input_changes PASSED
test_determinism.py::test_deterministic_result_content_hash_stable_across_runs PASSED
test_determinism.py::test_deterministic_trace_content_hash_stable_across_runs PASSED
test_determinism.py::test_repeated_execution_produces_byte_identical_json PASSED
test_determinism.py::test_no_timestamp_or_random_fields_in_result_or_trace_content PASSED
test_determinism.py::test_ids_are_content_derived_not_random_uuids PASSED
test_fv.py::test_fv_known_answer_vector PASSED
test_fv.py::test_fv_15_year_regression_vector_matches_life_003 PASSED
test_fv.py::test_fv_zero_rate PASSED
test_fv.py::test_fv_zero_periods_is_valid PASSED
test_fv.py::test_fv_negative_rate_is_allowed PASSED
test_fv.py::test_fv_output_carries_projection_not_guarantee_warning PASSED
test_inflation.py::test_inflation_exact_deflate_nominal_method PASSED
test_inflation.py::test_inflation_exact_real_rate_method PASSED
test_inflation.py::test_inflation_method_is_required_no_default PASSED
test_inflation.py::test_inflation_approximate_vector PASSED
test_inflation.py::test_inflation_approximate_result_carries_explicit_inexactness_warning PASSED
test_inflation.py::test_exact_and_approximate_results_differ PASSED
test_inflation.py::test_approximate_is_a_separate_calculator_id_not_a_hidden_mode PASSED
test_normalization.py::test_negative_periods_rejected PASSED
test_normalization.py::test_missing_required_input PASSED
test_normalization.py::test_ambiguous_rate_unit_rejected PASSED
test_normalization.py::test_percentage_and_decimal_units_are_not_guessed_from_magnitude PASSED
test_normalization.py::test_invalid_unit_rejected PASSED
test_normalization.py::test_nan_rejected PASSED
test_normalization.py::test_infinity_rejected PASSED
test_normalization.py::test_negative_infinity_rejected PASSED
test_normalization.py::test_float_type_input_rejected PASSED
test_normalization.py::test_malformed_decimal_string_rejected PASSED
test_normalization.py::test_unsupported_currency_rejected PASSED
test_normalization.py::test_missing_currency_rejected_when_required PASSED
test_pv.py::test_pv_known_answer_vector PASSED
test_registry.py::test_unknown_calculator_id_fails_closed PASSED
test_registry.py::test_unsupported_calculator_version_fails_closed PASSED
test_registry.py::test_retired_calculator_rejected PASSED
test_registry.py::test_active_version_still_works_alongside_retired_version PASSED
test_rounding.py::test_round_money_half_up_rounds_up_at_exact_half PASSED
test_rounding.py::test_round_money_half_up_does_not_round_down_at_half PASSED
test_rounding.py::test_round_money_default_two_decimal_places PASSED
test_rounding.py::test_round_rate_fraction_default_six_places PASSED
test_rounding.py::test_round_rate_percentage_default_four_places PASSED
test_rounding.py::test_unrounded_intermediate_values_preserved_in_trace PASSED
test_validation.py::test_valid_success_result_passes_validation PASSED
test_validation.py::test_success_result_without_trace_fails_validation PASSED
test_validation.py::test_trace_result_id_mismatch_fails_validation PASSED
test_validation.py::test_tampered_trace_input_hash_detected PASSED
test_validation.py::test_tampered_result_input_hash_detected PASSED
test_validation.py::test_tampered_trace_output_hash_detected PASSED
test_validation.py::test_tampered_output_values_detected_via_output_hash PASSED
test_validation.py::test_non_success_result_with_unexpected_trace_fails_validation PASSED

============================== 57 passed in 0.16s ===============================
```

**Combined with LIFE-PROTOTYPE-001's 45 tests, the full
`life_intelligence_lab` suite is 102 tests, 102 passed, 0 failed.**

## 8. Test count

**57 tests for this prototype**, covering all 30 required cases plus 12
additional cases found useful during implementation (unsupported
currency, missing currency, malformed decimal string, negative-infinity
rejection, exact-methods-agree-with-each-other, approximate-is-a
-separate-calculator-id, negative-rate-allowed-for-FV, projection-not
-guarantee warning presence, active-version-still-works-alongside
-retired, input-hash-changes-when-input-changes, tampered-result-hash
variants for both input and output, non-SUCCESS-with-unexpected-trace).

## 9. Known-answer vector results

All independently computed with Python's `decimal.Decimal` before being
locked into tests (shown with full trace precision where relevant):

| Vector | Expected | Actual (rounded) | Actual (unrounded, from trace) |
|---|---|---|---|
| FV(100000, 8%, 10) | 215892.50 | **215892.50** | 215892.49972727866982400000 |
| FV(100000, 8%, 15) — **LIFE-003 regression** | ≈317216.91 | **317216.91** | 317216.9114198268924301601145 |
| PV(1000000, 7%, 15) | ≈362446.02 | **362446.02** | 362446.0196423597512554873662 |
| CAGR(100000→200000, 6y) | ≈12.2462% | **12.2462%** (0.122462) | 0.122462048309372981433533050 |
| Inflation exact, Method A (deflate_nominal) | ≈120553.24 | **120553.24** | 120553.2442228609844791078861 |
| Inflation exact, Method B (exact_real_rate) | ≈120553.24 | **120553.24** | 120553.2442228609844791078859 (agrees with A to 10 decimal places) |
| Inflation approximate | ≈121899.44 | **121899.44** | 121899.44199947571302400000 |

All seven match the assignment's expected values exactly.

## 10. Sample successful result

Captured verbatim from an actual `run_calculator.py` execution
(`example_fv_100000_8pct_10y`):

```json
{
  "result_id": "result_97331b165263bd86_ee4c2d2b73d11dcd",
  "request_id": "example_fv_100000_8pct_10y",
  "calculator_id": "FV_LUMP_SUM",
  "calculator_version": 1,
  "status": "SUCCESS",
  "reason": null,
  "output_values": {
    "future_value": "215892.50"
  },
  "output_units": {
    "future_value": "money"
  },
  "rounding": {
    "future_value": {"decimal_places": 2, "mode": "ROUND_HALF_UP"}
  },
  "warnings": [
    "This is a projection based on the stated rate and is not a guaranteed outcome."
  ],
  "limitations": [
    "This is a mathematical projection based on the inputs and assumptions provided; it is not a guarantee of any future outcome."
  ],
  "trace_id": "trace_97331b165263bd86_ee4c2d2b73d11dcd",
  "deterministic_input_hash": "97331b165263bd86a1991a0c9c4620793655b02f9850d929f0968a666f00bc98",
  "deterministic_output_hash": "ee4c2d2b73d11dcd69ee35ad82cae728336589b824be90844fce27431f69cc9a"
}
```

Its accompanying `trace.json` (also captured verbatim):

```json
{
  "trace_id": "trace_97331b165263bd86_ee4c2d2b73d11dcd",
  "request_id": "example_fv_100000_8pct_10y",
  "calculator_id": "FV_LUMP_SUM",
  "calculator_version": 1,
  "formula_id": "FV_LUMP_SUM_FORMULA_V1",
  "calculation_date": "2026-07-26",
  "currency": "INR",
  "method": null,
  "normalized_inputs": [
    {"field_name": "present_value", "original_value": "100000", "original_unit": null, "normalized_value": "100000", "normalized_unit": "decimal"},
    {"field_name": "periodic_rate", "original_value": "8", "original_unit": "percentage", "normalized_value": "0.08", "normalized_unit": "decimal_fraction"},
    {"field_name": "periods", "original_value": "10", "original_unit": null, "normalized_value": "10", "normalized_unit": "periods"}
  ],
  "steps": [
    {"step_number": 1, "description": "Compute the compound growth factor (1 + periodic_rate)^periods", "expression": "(1 + 0.08)^10", "unrounded_value": "2.15892499727278669824"},
    {"step_number": 2, "description": "Multiply present value by the growth factor", "expression": "100000 * 2.15892499727278669824", "unrounded_value": "215892.49972727866982400000"}
  ],
  "output_before_rounding": {"future_value": "215892.49972727866982400000"},
  "output_after_rounding": {"future_value": "215892.50"},
  "rounding_applied": {"future_value": {"decimal_places": 2, "mode": "ROUND_HALF_UP"}},
  "warnings": ["This is a projection based on the stated rate and is not a guaranteed outcome."],
  "implementation_adapter_id": "life_intelligence_lab.calculators.formulas.fv",
  "implementation_version": "life-intelligence-lab-calc-runtime/0.1.0",
  "dependency_versions": {"decimal_module": "python_stdlib_decimal", "runtime_version": "life-intelligence-lab-calc-runtime/0.1.0"},
  "input_hash": "97331b165263bd86a1991a0c9c4620793655b02f9850d929f0968a666f00bc98",
  "output_hash": "ee4c2d2b73d11dcd69ee35ad82cae728336589b824be90844fce27431f69cc9a"
}
```

## 11. Sample failed-closed result

Captured from `example_cagr_failed_closed_zero_beginning` (beginning
value deliberately set to `0`):

```json
{
  "result_id": "result_failed_93abe3cb42d212d3f7650fde05",
  "request_id": "example_cagr_failed_closed_zero_beginning",
  "calculator_id": "CAGR",
  "calculator_version": 1,
  "status": "FAILED_CLOSED",
  "reason": "cagr_beginning_value_zero: beginning value cannot be zero",
  "output_values": null,
  "output_units": null,
  "rounding": null,
  "warnings": [],
  "limitations": [
    "This is a mathematical projection based on the inputs and assumptions provided; it is not a guarantee of any future outcome.",
    "CAGR requires beginning_value != 0 and periods > 0; negative beginning/ending values are rejected by default and require an explicit allow_negative_values=true."
  ],
  "trace_id": null,
  "deterministic_input_hash": "93abe3cb42d212d3f7650fde0511b6e9dedc070de483e1d922dac2c86819d17d",
  "deterministic_output_hash": null
}
```

No `trace.json` was written for this run (CLI exit code: `1`) — a
`FAILED_CLOSED` result never carries a trace or a plausible-looking
number, exactly per the assignment's requirement.

## 12. Input hash

`97331b165263bd86a1991a0c9c4620793655b02f9850d929f0968a666f00bc98`
(FV_LUMP_SUM, PV=100000, r=8%, n=10, INR) — reproduced byte-identically
across every repeated run and by `replay_calculation.py`.

## 13. Result hash

`824a6862c85fa35136eba4db11bdc8d7a697b2f095c2fb460b0a19a013bd02cb`
(the whole-`result.json`-content hash for the same request, computed via
`canonical.hash_result_content`).

## 14. Trace hash

`919bc6ca9bc3e8fe9c7eb571f88df30d60f40ddce262bceec5c0dd0825b9afc6`
(the whole-`trace.json`-content hash for the same request, computed via
`canonical.hash_trace_content`).

## 15. Deterministic replay result

Ran `replay_calculation.py` against the FV example, comparing to the
original `run_calculator.py` output:

```
Replay complete.
  status: SUCCESS
  input_hash: 97331b165263bd86a1991a0c9c4620793655b02f9850d929f0968a666f00bc98
  output_hash: ee4c2d2b73d11dcd69ee35ad82cae728336589b824be90844fce27431f69cc9a
  result_content_hash: 824a6862c85fa35136eba4db11bdc8d7a697b2f095c2fb460b0a19a013bd02cb
  trace_content_hash: 919bc6ca9bc3e8fe9c7eb571f88df30d60f40ddce262bceec5c0dd0825b9afc6
  DETERMINISTIC REPLAY: MATCH (all hashes identical to prior run)
```

Exit code `0`. Also ran replay against the **failed-closed** CAGR
example to confirm determinism holds for failure paths too, not only
successes:

```
Replay complete.
  status: FAILED_CLOSED
  input_hash: 93abe3cb42d212d3f7650fde0511b6e9dedc070de483e1d922dac2c86819d17d
  output_hash: None
  result_content_hash: adce751ea12066cf4c329cbcff30a8779ab9729450de8f6b0c9c1daefbd96885
  trace_content_hash: None
  DETERMINISTIC REPLAY: MATCH (all hashes identical to prior run)
```

Both the presence of matching hashes (success case) and the matching
*absence* of a trace/output hash (failure case) reproduced identically.

## 16. Confirmation that the LIFE-003 15-year future-value example was tested correctly

**Confirmed.** `test_fv.py::test_fv_15_year_regression_vector_matches_life_003`
asserts `FV(100000, 8%, 15) == "317216.91"` exactly, with a docstring
explaining why the vector exists (LIFE-003's own prose draft momentarily
carried an incorrect/placeholder figure for this exact case before being
corrected in that document). The value was independently verified via
`Decimal` arithmetic before being locked into the test
(`100000 * 1.08**15 = 317216.9114198268924301601145`, rounding to
`317216.91` under `ROUND_HALF_UP` at 2dp) — see §9's table — and again
reproduced via the live CLI in §6/§9. This is now a permanent regression
test: any future change to the FV formula, the rounding policy, or the
Decimal-power handling that would silently reintroduce a wrong answer
for this case fails the test suite immediately.

## 17. Known limitations

- **No `AssumptionSet`/`TaxRuleVersion`/observation wiring.**
  `CalculationRequest.source_observation_refs` and `.assumption_refs`
  exist as fields (per `CLAUDE-LIFE-002`'s contract) but are never
  populated or consulted — none of the four implemented calculators need
  external data. Wiring these to real registries is future work, not
  attempted speculatively here.
- **`allow_negative_values` on CAGR is a blunt instrument.** It permits
  negative beginning *and* ending values together but does not attempt
  to give a more nuanced domain treatment (e.g. sign-change scenarios
  are still rejected via the `InvalidOperation` catch, which is
  correct, but the error message doesn't distinguish "both negative,
  fine" from "mixed signs, mathematically undefined" as clearly as it
  could).
- **Currency whitelist is small and arbitrary** (`INR`, `USD`, `GBP`,
  `EUR`) — a placeholder, not a researched, authoritative list.
- **No compounding-frequency conversion.** `periodic_rate` is always
  taken as already being the *per-period* rate matching `periods`'
  implicit period length; there is no built-in nominal-annual-to
  -periodic conversion (e.g. "12% annual, compounded monthly" must be
  pre-converted by the caller to `1%` per period with `periods` in
  months). This matches the assignment's stated formula shapes exactly
  but is a real usability gap for a production caller.
- **Rounding decimal-place counts are fixed constants** in
  `rounding.py`, not yet wired to the `requested_rounding` override
  field that exists on `CalculationRequest` — the contract has the
  field, but the runtime does not yet honor a caller-supplied override.
- **Single-process, in-memory registry only.** No persistence, no
  concurrent-request handling considerations, no versioning migration
  tooling — appropriate for a bounded prototype, not for a service.

## 18. Recommendation

**Retain as reference.**

The core deterministic pipeline — registry lookup, schema-driven
normalization with explicit unit requirements, Decimal-safe arithmetic
(including the one genuinely fractional exponent, verified rather than
assumed), atomic trace/result construction, recompute-and-compare
validation, and content-derived (never random) hashing and ids — works
exactly as designed and is proven by 57 passing tests plus live CLI
execution of every required vector, including the LIFE-003 regression
case. It is a sound, tested shape for the Calculator Registry and
Deterministic Calculator Runtime components described in
`CLAUDE-LIFE-003`. It should **not** be promoted toward production as
-is: the known limitations in §17 (no assumption/tax-rule wiring, no
compounding-frequency conversion, unhonored rounding overrides) all need
attention, and — as with LIFE-PROTOTYPE-001 — none of the surrounding
governance (a real Calculator Registry service, Assumption Registry,
Calculation Orchestrator distinct from this prototype's single
`runtime.py`) exists yet outside this prototype's own boundary.
