# Prototype Report — LIFE-PROTOTYPE-003: Deterministic XIRR and Dated Cash-Flow Runtime

**Status: EXPERIMENTAL. NOT PRODUCTION READY. NOT CLAIMED TO BE.**

## 1. Files changed

**New:**
```
life_intelligence_lab/calculators/cash_flow.py
life_intelligence_lab/calculators/adapters/__init__.py
life_intelligence_lab/calculators/adapters/pyxirr_adapter.py
life_intelligence_lab/calculators/formulas/xirr.py
life_intelligence_lab/calculators/formulas/xnpv.py
life_intelligence_lab/calculators/formulas/irr_periodic.py
life_intelligence_lab/calculators/formulas/npv_periodic.py
life_intelligence_lab/examples/xirr_valid.json
life_intelligence_lab/examples/xnpv_valid.json
life_intelligence_lab/examples/irr_periodic_valid.json
life_intelligence_lab/examples/npv_periodic_valid.json
life_intelligence_lab/examples/xirr_zero_return.json
life_intelligence_lab/examples/xirr_duplicate_rejection.json
life_intelligence_lab/examples/xirr_duplicate_netting.json
life_intelligence_lab/examples/xirr_same_sign_failure.json
life_intelligence_lab/examples/xirr_multiple_root_warning.json
life_intelligence_lab/examples/xirr_no_root.json
life_intelligence_lab/tests/test_calculators/test_cash_flow.py
life_intelligence_lab/tests/test_calculators/test_pyxirr_adapter.py
life_intelligence_lab/tests/test_calculators/test_xirr.py
life_intelligence_lab/tests/test_calculators/test_xnpv.py
life_intelligence_lab/tests/test_calculators/test_periodic.py
life_intelligence_lab/tests/test_calculators/test_dated_determinism.py
life_intelligence_lab/PROTOTYPE_REPORT_003.md (this file)
```

**Modified:**
```
life_intelligence_lab/calculators/contracts.py       (additive: CashFlow, DuplicateDateOperation,
                                                        new vocabularies, new optional fields)
life_intelligence_lab/calculators/canonical.py         (additive: optional extra_content param)
life_intelligence_lab/calculators/serialization.py     (carries new optional fields through)
life_intelligence_lab/calculators/normalization.py     (additive: to_decimal_safe/validate_iso_date
                                                          public wrappers, FIELD_KIND_DECIMAL_LIST,
                                                          fixed a mislabeled error reason)
life_intelligence_lab/calculators/formulas/__init__.py (additive: DomainError.root_status,
                                                          FormulaOutput's 3 new optional fields)
life_intelligence_lab/calculators/rounding.py          (fixed: negative-zero normalization)
life_intelligence_lab/calculators/registry.py           (additive: 4 new CalculatorDefinition entries)
life_intelligence_lab/calculators/runtime.py             (additive: cash-flow normalization step,
                                                            dependency-failure handling, dispatch
                                                            table extended to 3-arg signature)
life_intelligence_lab/calculators/validation.py          (fixed: extra_content reconstruction for
                                                            hash recomputation; additive: 3 new
                                                            dated-specific checks)
life_intelligence_lab/requirements.txt                    (pinned pyxirr==0.10.8, sandbox-only)
life_intelligence_lab/README.md                            (pointer section)
life_intelligence_lab/CALCULATOR_RUNTIME_README.md          (Prototype 003 addendum)
life_intelligence_lab/CALCULATOR_ARCHITECTURE.md             (Prototype 003 addendum)
```

**Untouched:** everything from LIFE-PROTOTYPE-001 (`downloader.py`,
`parser.py`, root-level `contracts.py`/`canonical.py`/`validation.py`),
and all four LIFE-PROTOTYPE-002 formula modules (`fv.py`, `pv.py`,
`cagr.py`, `inflation_adjusted*.py`) — none of their source files were
modified.

## 2. Dependency and exact version

**pyxirr, version 0.10.8** — installed via `pip install pyxirr==0.10.8 --break-system-packages`.

## 3. Licence

**Unlicense** (public domain equivalent) — confirmed via `pip show pyxirr`:
```
Name: pyxirr
Version: 0.10.8
Summary: Rust-powered collection of financial functions for Python.
Home-page: https://github.com/Anexen/pyxirr
License: Unlicense
```

## 4. Installation result

Succeeded on the first attempt, no build issues (pyxirr ships prebuilt
Rust wheels). `INSTALLED_DEPENDENCY_VERSION == PINNED_DEPENDENCY_VERSION`
is asserted by `test_pyxirr_adapter.py::test_installed_version_matches_pinned_version`
and passes in this environment.

**Maintenance/platform concern worth recording:** this pinned version's
`DayCount` enum has **no plain `ACT_365` member** — only `ACT_365F`,
`ACT_365_25`, `ACT_360`, `ACT_364`, `ACT_ACT_ISDA`, `NL_360`, `NL_365`,
and several `THIRTY_*` variants. The assignment's `ACT_365` was mapped to
`ACT_365F` ("Actual/365 Fixed" — days/365 regardless of leap year),
**verified empirically** to reproduce the exact expected known-answer
XIRR vector before being relied on anywhere (§7 below). A future pyxirr
upgrade could rename or restructure this enum; `PyXirrAdapter.resolve_day_count`
is the single place that mapping would need to change.

## 5. Dependency fingerprint

```
pyxirr==0.10.8+life_intelligence_lab.calculators.adapters.pyxirr_adapter.PyXirrAdapter@pyxirr-adapter/0.1.0
```

Computed by `adapters/pyxirr_adapter.py::dependency_fingerprint()`,
embedded in every dated calculator's `CalculationTrace.dated_cash_flow_context`,
and independently **recomputed and compared** (not merely re-trusted) by
`validation.py::validate_result`'s new `dependency_fingerprint_matches` check.

## 6. Commands to run

```bash
cd <parent of life_intelligence_lab/>

python -m life_intelligence_lab.scripts.run_calculator \
  --calculator XIRR_DATED --version 1 --input life_intelligence_lab/examples/xirr_valid.json

python -m life_intelligence_lab.scripts.replay_calculation \
  --request life_intelligence_lab/examples/xirr_valid.json \
  --compare-to life_intelligence_lab/data/calculations/example_xirr_valid

python -m pytest life_intelligence_lab/tests -q
```

The existing CLI scripts from Prototype 002 needed **no modification** —
`execute_calculation_request` remained the single entry point both call.

## 7. Test command and output

`python -m pytest life_intelligence_lab/tests -q`, run from the repository root:

```
........................................................................ [ 40%]
........................................................................ [ 80%]
....................................                                     [100%]
180 passed in 0.28s
```

## 8. New test count

**78 new tests** (well above the required 45 minimum):

| File | Count | Covers |
|---|---|---|
| `test_cash_flow.py` | 19 | CashFlow normalization, both duplicate-date policies, zero-net, ordering permutation, precision, malformed input |
| `test_pyxirr_adapter.py` | 12 | Adapter containment, version pin, fingerprint, day-count mapping, dependency-failure injection |
| `test_xirr.py` | 14 | Known-answer vector, all adversarial sign/root cases, dependency-failure injection, duplicate policies at runtime level |
| `test_xnpv.py` | 7 | Consistency at the XIRR root, rate ≤ -1, ambiguous rate unit |
| `test_periodic.py` | 10 | Periodic IRR/NPV known-answer, adversarial cases, periodic/dated terminology separation |
| `test_dated_determinism.py` | 16 | Hash determinism, permutation invariance, Prototype 002 hash preservation, tamper detection (5 distinct tamper vectors) |

## 9. Combined test count

**180 passed** (102 pre-existing from Prototype 001/002 + 78 new). All
102 pre-existing tests pass **unmodified** — none were edited to
accommodate Prototype 003.

## 10. XIRR known-answer result

Cash flows: `2020-01-01 -10000`, `2020-03-01 5750`, `2020-10-30 4250`,
`2021-02-15 3250`, convention `ACT_365`.

**Full returned precision (via the pinned pyxirr, before any rounding):**
```
0.6342972615260243
```
**Rounded output (6dp decimal / 4dp percentage, as delivered by the CLI):**
```
rate: 0.634297
rate_percentage: 63.4297
```
`root_status: SINGLE_ROOT`. Matches the assignment's expected `≈0.63429726`.

## 11. XNPV consistency value and tolerance

Using the XIRR rate above as the XNPV rate over the same cash flows:

```
Full XNPV value (unrounded, via pyxirr): -2.2737367544323206E-13
Declared absolute tolerance: 0.01
Within tolerance: True
Rounded display value: 0.00
```
Recorded verbatim in `trace.dated_cash_flow_context["xnpv_consistency_check"]`
and independently re-verified by `validation.py`'s new
`xnpv_consistency_within_tolerance` check.

## 12. Periodic IRR result

Cash flows: `-250000, 100000, 150000, 200000, 250000, 300000`.

**Full returned precision:** `0.5672303344358535`
**Rounded output:** `rate: 0.567230`, `rate_percentage: 56.7230`
`root_status: SINGLE_ROOT`. Matches the assignment's expected `≈0.56723033`.

## 13. Zero-return result

Cash flows: `2020-01-01 -1000`, `2021-01-01 1000` (no growth, ACT_365).

```
Status: SUCCESS
rate: 0.000000
rate_percentage: 0.0000
root_status: SINGLE_ROOT
```
Zero is treated as a fully valid numeric `SUCCESS` result, not a failure
or an absent value — confirmed by
`test_xirr.py::test_zero_xirr_is_a_valid_success_not_a_failure` and
reproduced via the live CLI (`examples/xirr_zero_return.json`).

## 14. Multiple-root result

Cash flows: `2020-01-01 -100`, `2020-06-01 1000`, `2020-12-01 -100`,
`2021-06-01 -1000` (two chronological sign changes: −→+, +→−).

```
Status: SUCCESS
rate: 0.248677
rate_percentage: 24.8677
root_status: MULTIPLE_ROOTS_POSSIBLE
warnings: ["MULTIPLE ROOTS POSSIBLE: 2 sign changes were detected in these cash
flows (chronological order). The returned rate is a CANDIDATE root only, not
guaranteed to be the unique or economically correct one. Do not treat it as
authoritative without independent review."]
```
The candidate is returned, never discarded, but is explicitly and
permanently distinguished from a `SINGLE_ROOT` result.

## 15. No-root / dependency-failure result

**No-root** (genuine — pyxirr's own solver returns `None` despite a
valid, multi-sign-change cash-flow list; verified empirically before
being used as a test/example vector):

Cash flows: `2020-01-01 -1000`, `2021-01-01 3000`, `2022-01-01 -2500`.
```
Status: FAILED_CLOSED
Reason: xirr_no_root_found: no_root_found_or_non_convergent
root_status: MULTIPLE_ROOTS_POSSIBLE
trace: None, output_values: None
```

**Dependency failure** (simulated via adapter engine injection —
deterministic, not a flaky live failure):
```
Status: FAILED_CLOSED
Reason: dependency_failure: RuntimeError: simulated catastrophic engine failure
root_status: DEPENDENCY_FAILURE
trace: None, output_values: None
```

## 16. Sample successful result

Captured verbatim from `run_calculator.py` against `examples/xirr_valid.json`:
```
Status: SUCCESS
Output: {'rate': '0.634297', 'rate_percentage': '63.4297'}
Warnings: []
Input hash: d9508147af41de12ac9ee884f18c597dcff1d58a2725c1fcff5a9f2b2ae565a2
Output hash: afa7ba529536c1797b4a91f0d5566e2d3a77f1c6eb888e6dbfc22b6e90f1cf45
```

## 17. Sample failed-closed result

Captured verbatim from `run_calculator.py` against
`examples/xirr_same_sign_failure.json`:
```
Status: FAILED_CLOSED
Reason: xirr_requires_at_least_one_positive_and_one_negative_flow
Input hash: 93acb3ae3e243ba822a775174195cae8b470f1bbe4685ccb358f93c296463d21
Output hash: None
```
`root_status: INVALID_CASH_FLOWS`. No trace, no output values — no
plausible-looking rate anywhere in this result.

## 18. Input hash

`d9508147af41de12ac9ee884f18c597dcff1d58a2725c1fcff5a9f2b2ae565a2`
(`XIRR_DATED`, the known-answer vector) — reproduced byte-identically
across every repeated run and by `replay_calculation.py`.

## 19. Result hash

`822074017690f47243e7355144434daccb369d913103be1dd2ad321f213821fe`
(whole-`result.json`-content hash for the same request, via
`canonical.hash_result_content`).

## 20. Trace hash

`5e9f2eeec0070cb105027ff95ffae4c22d6cf21ab09bf1dceb16d0d2f4f5b2cd`
(whole-`trace.json`-content hash, via `canonical.hash_trace_content`).

## 21. Deterministic replay results

All four required demonstrations, run via the live CLI against the
committed `data/calculations/` outputs:

| Case | Status | Result |
|---|---|---|
| Successful XIRR (`xirr_valid.json`) | SUCCESS | **MATCH** — all 4 hashes identical |
| Successful XNPV (`xnpv_valid.json`) | SUCCESS | **MATCH** — all 4 hashes identical |
| Failed-closed (`xirr_same_sign_failure.json`) | FAILED_CLOSED | **MATCH** — input hash and result-content hash identical; output/trace hashes both `None` on both sides |
| Multiple-root (`xirr_multiple_root_warning.json`) | SUCCESS, `MULTIPLE_ROOTS_POSSIBLE` | **MATCH** — all 4 hashes identical |

Exit code `0` in every case. Also verified: extending the shared
contracts for Prototype 003 did **not** change Prototype 002's
already-published hash for the FV example
(`97331b165263bd86a1991a0c9c4620793655b02f9850d929f0968a666f00bc98`,
still exact) — see `test_dated_determinism.py::test_prototype_002_hash_unaffected_by_prototype_003_extension`.

## 22. Known limitations

- **Only `ACT_365` day-count is supported**, mapped to pyxirr's
  `ACT_365F`. Any other convention is rejected outright, not approximated.
- **`NON_CONVERGENT` is defined but currently unreachable as a distinct
  outcome from `NO_ROOT_FOUND`.** The pinned pyxirr version signals both
  "no root exists" and "solver failed to converge" identically (a bare
  `None` return, no distinguishing detail) — this prototype does not
  fabricate a distinction the dependency doesn't actually provide.
- **Duplicate-date netting provenance ordering** (the order of
  `original_cash_flow_ids` *within* a single `DuplicateDateOperation`,
  when duplicate same-date entries are themselves reordered relative to
  each other) is not independently verified permutation-invariant — a
  narrower case than general cash-flow-list ordering, which *is*
  verified (`test_cash_flow_order_permutation_does_not_change_hash`).
- **No bounded root scan.** Only the single candidate pyxirr's solver
  returns is surfaced; the prototype does not attempt to enumerate or
  bracket multiple roots itself, consistent with the assignment's
  "optionally implement... if it can be done deterministically and
  safely" — it was not attempted here to stay within scope.
- **Two real bugs were found and fixed during development**, both via
  the test suite catching them rather than being anticipated in advance:
  (1) a `cash_flow_id` derivation that depended on input-order-derived
  `sequence`, silently breaking permutation invariance; (2) a hash
  -validation gap where `validate_result` didn't reconstruct the
  cash-flow-derived `extra_content` before recomputing `input_hash`,
  which would have made every legitimate dated-calculator result
  incorrectly report as tamper-invalid. Both are now covered by
  regression tests (`test_cash_flow_order_permutation_does_not_change_hash`,
  the full `test_dated_determinism.py` tamper-detection suite).
- **Currency whitelist remains the same small, arbitrary list** inherited
  from Prototype 002 (`INR`, `USD`, `GBP`, `EUR`).
- **Single-process, in-memory registry only** — same caveat as Prototype 002.

## 23. Recommendation

**Retain as reference.**

The dated cash-flow pipeline — explicit day-count and duplicate-date
policies, a fully contained third-party solver adapter with injectable
-engine testability, honest (never fabricated) multiple-root labelling,
and hash/validation machinery correctly extended to cover cash-flow
content without disturbing Prototype 002 — works exactly as designed and
is proven by 78 new tests (180 total), live CLI execution of every
required known-answer and adversarial vector, and four independent
deterministic-replay demonstrations. It is a sound, tested shape for the
dated-cash-flow portion of `CLAUDE-LIFE-003`'s calculator layer. It
should **not** be promoted toward production as-is: only one day-count
convention is supported, `NON_CONVERGENT` is not genuinely distinguishable
from `NO_ROOT_FOUND` given the pinned dependency's actual behavior, and —
as with both prior prototypes — none of the surrounding governance (a
real Calculator Registry service, Assumption Registry, multi-process
concerns) exists yet outside this prototype's own boundary.
