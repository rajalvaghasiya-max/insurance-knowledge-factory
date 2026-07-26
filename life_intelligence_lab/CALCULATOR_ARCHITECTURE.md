# Architecture Note — Deterministic TVM Calculator Runtime

## Why calculators are registered

Every formula that can ever run lives in exactly one place:
`calculators/registry.py`'s `_CALCULATORS` dict, populated once, at
import time, entirely from code — never from a request. `runtime.py`'s
`execute_calculation_request` can only ever look up an existing
`(calculator_id, calculator_version)` pair there; there is no code path
by which a request adds, replaces, or extends an entry. This is what
makes "the runtime may invoke only a registered calculator ID and
version" a structural property of the lookup mechanism, not a rule that
has to be remembered and separately enforced at every call site.

## Why agents cannot supply formulas

Two separate mechanisms make this true, not one:

1. **The dispatch table is fixed, code-defined data.** `runtime.py`'s
   `_DISPATCH` dict maps a calculator id to a Python function reference,
   written once in source. A request's `calculator_id` is a *lookup key*
   into that table — never a string that gets `eval`'d, `exec`'d, or
   dynamically imported based on request content. `contracts.py`'s
   `CalculationTrace` docstring makes this explicit: `expression` fields
   in trace steps are always display strings, never anything executed.
2. **Formula modules only ever receive already-normalized Decimal
   values**, never raw request text. By the time `formulas/fv.py`'s
   `compute()` runs, every input has already passed through
   `normalization.py`'s schema-driven, calculator-defined validation — a
   formula module has no visibility into, and no use for, the original
   request's raw strings.

A future "calculator-selection agent" (per `CLAUDE-LIFE-003`'s agent
boundary) can only ever choose among registry entries that already
exist; it has no mechanism available to construct a new one.

## Why rates require explicit units

`8` is not self-describing: it could mean `8%` (a modest return) or a
decimal `8` (`800%`, a wildly different number). `normalization.py`'s
`_normalize_rate_field` refuses to convert *any* rate-kind field unless
`input_units` names it as exactly `"decimal"` or `"percentage"` — there
is no default, and no branch of the code infers a unit from a value's
magnitude. This directly implements the assignment's "do not guess
whether `8` means `8%` or `800%`" instruction as a hard rejection
(`ambiguous_rate_unit`) rather than a heuristic.

## Why result and trace are atomic

`runtime.py` constructs `CalculationResult` and `CalculationTrace`
together, in the same function, from the same `formula_output`, and
returns them as a pair — there is no intermediate state where a result
exists without its trace (for `SUCCESS`) or where a trace exists without
a result. `validation.py`'s `validate_result` enforces this as an
invariant: a `SUCCESS` result with `trace=None` is *always* invalid
(`trace_missing_for_success`), and every non-`SUCCESS` result is
required to have `trace=None`, `output_values=None`, and
`deterministic_output_hash=None` — there is no partial-failure shape
that could carry a stray, unexplained number.

## How Decimal and exponentiation are handled

Every calculator in this prototype does its arithmetic in
`decimal.Decimal`, never `float`, from input to final rounding:

- **Money and rates enter as `Decimal`, never `float`.**
  `normalization._to_decimal_safe` explicitly rejects the Python `float`
  type outright (`malformed_decimal_value: float type not accepted
  directly`) — a caller must quote a number as a JSON string so it goes
  through `Decimal(str)` construction, never through an IEEE-754
  round-trip.
- **Integer-exponent compounding (`FV`, `PV`, and both inflation
  calculators) uses `Decimal ** int`**, which Python's `decimal` module
  computes exactly via repeated squaring — no precision boundary is
  crossed at all for these three formulas.
- **`CAGR`'s `(1/n)` exponent is genuinely fractional**, and this is the
  one place in the prototype where a fractional power is computed. This
  was verified empirically before being relied on:
  `Decimal(2) ** Decimal('0.5')` returns a correctly-rounded result
  using Python decimal's built-in support for the General Decimal
  Arithmetic specification's power operation — no fallback to `float`
  is needed or used. A negative base raised to a fractional exponent
  correctly raises `decimal.InvalidOperation` (no math for a fractional
  root of a negative real number exists), which `formulas/cagr.py`
  catches and re-raises as a `DomainError`
  (`cagr_undefined_for_input_combination`) rather than letting a raw
  `Decimal` exception propagate.
- **Rounding happens exactly once, at the very end**, via
  `rounding.py`'s `round_money`/`round_rate_fraction`/
  `round_rate_percentage`, all using `ROUND_HALF_UP` as documented.
  Every intermediate value — visible in `CalculationTrace.steps[*].unrounded_value`
  and `output_before_rounding` — stays full-precision Decimal until that
  single final step.

## How deterministic hashing works

Two hashes are computed for every successful calculation
(`canonical.py`):

- **`input_hash`** — a SHA-256 over a canonical JSON payload of exactly
  `(calculator_id, calculator_version, calculation_date, currency,
  method, normalized_inputs)`, with `normalized_inputs`' keys sorted so
  the hash never depends on dict iteration order.
- **`output_hash`** — a SHA-256 over `(output_after_rounding,
  output_units)`, similarly key-sorted.

Both hashes are propagated identically into both the `CalculationTrace`
and the `CalculationResult` (never recomputed differently in each), and
both `trace_id` and `result_id` are *derived* from these two hashes
(`trace_<input_hash[:16]>_<output_hash[:16]>`, etc.) rather than
generated as random UUIDs — there is no `uuid4()` call, and no wall
-clock value, anywhere in the id-generation or hashing path. This is
what makes the "no random IDs inside hashed content" and "repeated
execution produces byte-identical output" requirements hold
simultaneously: identical input always produces identical ids, not just
identical hash *values* alongside different ids.

The one place wall-clock time legitimately appears is
`run_metadata.json`, written by `output_writer.py` alongside
`result.json`/`trace.json` but never read by anything that computes a
hash — exactly mirroring LIFE-PROTOTYPE-001's `run_metadata.json`
pattern (reimplemented here, not imported, per the no-AMFI-dependency
boundary).

`validation.py`'s `validate_result` never *trusts* a stored hash — it
always **recomputes** `input_hash` from the trace's own
`normalized_inputs`/`calculation_date`/`currency`/`method`, and
`output_hash` from the trace's own `output_after_rounding`, then
compares. This is what actually catches tampering: mutating a stored
hash string, or the trace content the hash was derived from, is
detected because the check is a fresh recomputation, not a string
comparison against another stored string that could have been mutated
in the same way.

## Why this prototype has no dependency on the AMFI adapter

`life_intelligence_lab/calculators/` does not import `downloader.py`,
`parser.py`, or the root-level `contracts.py`/`canonical.py` built by
LIFE-PROTOTYPE-001, even though both prototypes share the same general
pattern (fixed field order, compact deterministic JSON, SHA-256,
separated run-metadata). The assignment explicitly required this
("[d]o not make the calculator runtime depend on AMFI-specific code"),
and it also happens to be the right design independent of that
instruction: a TVM calculator has no reason to know what a `SFIN` or an
`AMFI scheme code` is, and coupling the two would make either prototype
harder to evolve (or discard) independently. Where a *pattern* is
genuinely generic (canonical serialization, hash-then-compare
determinism), it is reimplemented fresh in `calculators/canonical.py`
rather than imported — a small amount of duplication in exchange for
zero coupling between two subsystems that should be able to change
independently.

## How this could later sit behind PolicyScna's governed contracts

This prototype's `CalculationRequest`/`CalculationResult`/
`CalculationTrace`/`CalculatorDefinition` shapes are deliberately close
to — but not the same as, and not imported from — the contracts
described in `CLAUDE-LIFE-002` §7 and `CLAUDE-LIFE-003` §5. A future
production runtime could reuse this prototype's structure directly:

- The fixed dispatch table (`runtime._DISPATCH`) is exactly the
  mechanism `CLAUDE-LIFE-003`'s Calculator Registry component describes
  — this prototype is a working, tested instance of "the runtime may
  invoke only a registered calculator ID and version."
- `validate_result`'s recompute-and-compare pattern is a working
  instance of `CLAUDE-LIFE-003`'s Calculation Validator component.
- The `AssumptionSet`/`TaxRuleVersion` references that
  `CLAUDE-LIFE-002`'s `CalculationRequest` contract calls for are
  present as empty placeholder fields (`source_observation_refs`,
  `assumption_refs`) in this prototype's `CalculationRequest`, but are
  never populated or consulted by anything — none of the four
  implemented calculators need external observations or governed
  assumptions, so wiring those references to a real Assumption
  Registry/Observation Registry is deliberately left for a future
  prototype, not implemented speculatively here.

None of that wiring exists yet. This prototype proves the deterministic
core in isolation, exactly as LIFE-PROTOTYPE-001 proved the deterministic
data-ingestion core in isolation.

---

# LIFE-PROTOTYPE-003 addendum — Dated Cash-Flow Runtime

## Why XIRR is registered (not computed ad hoc)

Exactly the same reason as every Prototype 002 calculator: `XIRR_DATED`
is a `CalculatorDefinition` entry in `registry.py`, looked up by
`(calculator_id, calculator_version)` through the identical
`runtime.execute_calculation_request` dispatch mechanism. Nothing about
adding a *dated* calculator required a second orchestrator — the same
"the runtime may invoke only a registered calculator ID and version"
guarantee that already held for `FV_LUMP_SUM` holds for `XIRR_DATED`
without modification.

## Why the numerical engine is hidden behind an adapter

`calculators/adapters/pyxirr_adapter.py::PyXirrAdapter` is the ONLY file
in this codebase that imports `pyxirr`. Every formula module
(`xirr.py`, `xnpv.py`, `irr_periodic.py`, `npv_periodic.py`) receives a
`PyXirrAdapter` instance (or constructs a default one) and calls its
methods (`.xirr()`, `.xnpv()`, `.irr_periodic()`, `.npv_periodic()`) —
never `pyxirr.xirr()` directly. This buys three things:

1. **Replaceability.** Swapping `pyxirr` for a different solver would
   mean rewriting `PyXirrAdapter`'s internals; no `CalculatorDefinition`,
   no formula module's public interface, and no caller changes.
2. **Testability without a real failure.** `PyXirrAdapter.__init__`
   accepts an injectable `engine` (default: the real `pyxirr` module).
   Tests pass a fake engine that raises an arbitrary exception,
   proving `DependencyFailureError` handling deterministically — the
   same dependency-injection pattern LIFE-PROTOTYPE-001 used for its
   HTTP `fetch_fn`.
3. **Absorbing the dependency's actual failure vocabulary.** pyxirr
   signals "no root" and "rate ≤ -1" by returning `None` (not raising),
   and signals "wrong sign pattern" via its own `InvalidPaymentsError`.
   The adapter is where these three genuinely different behaviors get
   translated into one uniform `SolveOutcome` shape
   (`converged`/`value`/`error_reason`) — no caller of the adapter needs
   to know pyxirr's specific quirks.

## Why day-count is explicit

`ACT_365` must be named in every `XIRR_DATED`/`XNPV_DATED` request
(`day_count_convention` in `input_values`) — there is no default. This
matters concretely: this pinned pyxirr version's `DayCount` enum has
**no plain `ACT_365` member** at all (only `ACT_365F`, `ACT_365_25`,
etc.). The mapping `"ACT_365" -> DayCount.ACT_365F` in
`pyxirr_adapter.py`'s `_DAY_COUNT_MAP` was **verified empirically**
before being relied on: `PyXirrAdapter().xirr(...)` with that mapping
reproduces the assignment's exact expected known-answer vector
(`0.6342972615260243`) — see `PROTOTYPE_REPORT_003.md`. Had this mapping
been assumed instead of checked, the whole calculator would have quietly
computed correct-looking but subtly wrong answers for every real
request; this is exactly the class of error explicit, tested, recorded
conventions exist to prevent.

## Why duplicate-date handling is explicit

`duplicate_date_policy` is a required input with no default, same
reasoning as day-count. `NET_SAME_DATE` never runs unless a caller
selects it, and even then the netting is never invisible: every original
flow and the netting operation (`DuplicateDateOperation`, with the
original ids, original amounts, and net amount) is retained in
`CalculationTrace.dated_cash_flow_context`. A same-date net that sums to
exactly zero is kept as an explicit zero-amount flow rather than
dropped — dropping would be a second, silent transformation stacked on
top of the first, and "silently" is precisely what this policy forbids.

## Why multiple roots are not silently resolved

`formulas/xirr.py` counts chronological sign changes itself (a pure,
dependency-free function, `count_sign_changes` in the adapter module) —
it does not ask pyxirr whether the cash flows are "conventional." More
than one sign change sets `root_status=MULTIPLE_ROOTS_POSSIBLE` and
attaches an explicit warning; the candidate rate pyxirr returned is still
surfaced (never discarded), but is never labelled `SINGLE_ROOT` and
never described as economically correct. `root_handling_policy` on the
`CalculatorDefinition` names this as a specific PolicyScna convention
(candidate-labelling, not root-selection) rather than an implicit
inheritance of "whatever the dependency happened to return."

## Why same-sign flows fail closed

An all-positive or all-negative cash-flow list is well-formed (every
individual date/amount/currency parses fine) but has no rate of return
to compute — there is nothing to solve for. This is a `DomainError`
(not a `NormalizationError`): the same INVALID_INPUT-vs-FAILED_CLOSED
distinction Prototype 002 established for CAGR's zero-beginning-value
case applies identically here, tagged
`root_status=INVALID_CASH_FLOWS`. The precondition is checked in the
formula module itself, *before* the adapter is even called — so this
never depends on however pyxirr happens to react to a same-sign list
(which, empirically, is its own `InvalidPaymentsError`, but PolicyScna's
own check runs first and does not rely on that dependency behavior).

## How dependency versions participate in replay

`PyXirrAdapter`'s module-level `INSTALLED_DEPENDENCY_VERSION` (read from
`pyxirr.__version__` at import time) and `dependency_fingerprint()`
(combining dependency name, installed version, adapter id, and adapter
version into one string) are embedded in every dated calculator's
`CalculationTrace.dated_cash_flow_context`. `validation.py`'s
`validate_result` **recomputes** this fingerprint live and compares it
against what the trace recorded — if a different pyxirr version were
installed later and a replay attempted, the mismatch would be caught by
`dependency_fingerprint_matches`, not silently ignored. Within a single
environment (as in this sandbox), the fingerprint is identical across
runs, which is what makes byte-identical replay possible at all — replay
determinism assumes the pinned dependency hasn't moved underneath it,
and that assumption is now a checked one, not an implicit one.

## A note on hash extension without disrupting Prototype 002

Two different cash-flow lists must hash differently, so
`canonical.hash_input` gained an optional `extra_content` parameter,
included in the hashed payload only when not `None`. Every Prototype 002
calculator never passes it, so their hash payload — and therefore their
hash *value* — is byte-for-byte unchanged; this was verified directly
against the exact hash already published in `PROTOTYPE_REPORT_002.md`
(`test_prototype_002_hash_unaffected_by_prototype_003_extension`).
`CashFlow.sequence` (original input position) is deliberately excluded
from what gets hashed, even though it's a real field: two logically
identical cash-flow sets entered in different order must hash
identically (`test_cash_flow_order_permutation_does_not_change_hash`) —
this was caught as a real bug during development (a first implementation
folded `sequence` into both the id derivation and the hash content,
which broke permutation invariance) and fixed by deriving
`cash_flow_id` from content alone and excluding `sequence` from the hash
basis specifically, while still keeping it in the human-readable trace
for provenance.
