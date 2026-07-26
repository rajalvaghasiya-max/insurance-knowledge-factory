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
