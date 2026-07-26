"""
life_intelligence_lab.calculators.contracts
============================================

Data contracts for the deterministic TVM calculator runtime.

Prototype-only shapes that intentionally mirror -- but do not import from,
and are not identical to -- the CalculationRequest/CalculationResult/
CalculationTrace/AssumptionSet contracts described in PolicyScna's
CLAUDE-LIFE-002/003 design documents.

Field ordering in each dataclass is deliberate and fixed: it is the
ordering used for deterministic canonical serialization (see
`canonical.py`). Do not reorder fields casually.
"""

from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional

RUNTIME_VERSION = "life-intelligence-lab-calc-runtime/0.1.0"

# --- Status vocabularies (closed sets, never free text) --------------------

CALCULATOR_STATUS_ACTIVE = "active"
CALCULATOR_STATUS_RETIRED = "retired"

RESULT_STATUS_SUCCESS = "SUCCESS"
RESULT_STATUS_FAILED_CLOSED = "FAILED_CLOSED"
RESULT_STATUS_INVALID_INPUT = "INVALID_INPUT"
RESULT_STATUS_UNSUPPORTED_CALCULATOR = "UNSUPPORTED_CALCULATOR"
RESULT_STATUS_VALIDATION_FAILED = "VALIDATION_FAILED"

TERMINAL_RESULT_STATUSES = {
    RESULT_STATUS_SUCCESS,
    RESULT_STATUS_FAILED_CLOSED,
    RESULT_STATUS_INVALID_INPUT,
    RESULT_STATUS_UNSUPPORTED_CALCULATOR,
    RESULT_STATUS_VALIDATION_FAILED,
}

# Input-field "kind" vocabulary used by CalculatorDefinition.required_input_schema
FIELD_KIND_MONEY = "money"        # decimal-safe currency amount
FIELD_KIND_DECIMAL = "decimal"    # decimal-safe plain magnitude (no currency)
FIELD_KIND_RATE = "rate"          # decimal-safe rate; MUST carry an explicit unit
FIELD_KIND_COUNT = "count"        # non-negative integer period count
FIELD_KIND_STRING = "string"      # short enumerated/whitelisted string (e.g. currency code)
FIELD_KIND_FLAG = "flag"          # boolean
FIELD_KIND_CASH_FLOW_LIST = "cash_flow_list"    # list of dated {date, amount, ...} objects
FIELD_KIND_DECIMAL_LIST = "decimal_list"        # list of plain decimal-safe amounts (periodic, undated)

# --- Prototype 003: dated cash-flow vocabularies ----------------------------

DAY_COUNT_ACT_365 = "ACT_365"
SUPPORTED_DAY_COUNT_CONVENTIONS = (DAY_COUNT_ACT_365,)  # minimum required; see ARCHITECTURE note

DUPLICATE_DATE_POLICY_REJECT = "REJECT_DUPLICATES"
DUPLICATE_DATE_POLICY_NET = "NET_SAME_DATE"
SUPPORTED_DUPLICATE_DATE_POLICIES = (DUPLICATE_DATE_POLICY_REJECT, DUPLICATE_DATE_POLICY_NET)

ROOT_STATUS_SINGLE_ROOT = "SINGLE_ROOT"
ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE = "MULTIPLE_ROOTS_POSSIBLE"
ROOT_STATUS_NO_ROOT_FOUND = "NO_ROOT_FOUND"
ROOT_STATUS_NON_CONVERGENT = "NON_CONVERGENT"
ROOT_STATUS_INVALID_CASH_FLOWS = "INVALID_CASH_FLOWS"
ROOT_STATUS_DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
ROOT_STATUS_VALUES = {
    ROOT_STATUS_SINGLE_ROOT,
    ROOT_STATUS_MULTIPLE_ROOTS_POSSIBLE,
    ROOT_STATUS_NO_ROOT_FOUND,
    ROOT_STATUS_NON_CONVERGENT,
    ROOT_STATUS_INVALID_CASH_FLOWS,
    ROOT_STATUS_DEPENDENCY_FAILURE,
}


@dataclasses.dataclass(frozen=True)
class CalculatorDefinition:
    """
    A single registered, versioned calculator. This is the ONLY legitimate
    source of a formula anywhere in the runtime -- nothing else may define
    how a number is computed, and no request-supplied text is ever
    executed as a formula (see ARCHITECTURE.md).
    """

    calculator_id: str
    calculator_version: int
    display_name: str
    formula_id: str
    formula_description: str
    required_input_schema: Dict[str, dict]  # field_name -> {"kind":..., "required":..., ...}
    output_schema: Dict[str, str]           # output_field_name -> "money" | "decimal"
    supported_units: List[str]              # e.g. ["decimal", "percentage"] for rate fields
    supported_methods: List[str]            # e.g. [] or ["deflate_nominal", "exact_real_rate"]
    compounding_convention: str             # e.g. "annual, discrete compounding"
    timing_convention: str                  # e.g. "n/a (single-point valuation)"
    rounding_policy: Dict[str, object]      # e.g. {"money_decimal_places": 2, "mode": "ROUND_HALF_UP"}
    implementation_adapter_id: str          # which formulas.* module implements this
    status: str                             # CALCULATOR_STATUS_ACTIVE | _RETIRED
    requires_currency: bool = False         # if True, CalculationRequest.currency is required and validated
    requires_cash_flows: bool = False       # if True, CalculationRequest.cash_flows is normalized via cash_flow.py
    supersedes: Optional[str] = None        # calculator_id:version this one replaces, if any
    supported_day_count_conventions: List[str] = dataclasses.field(default_factory=list)
    supported_duplicate_date_policies: List[str] = dataclasses.field(default_factory=list)
    root_handling_policy: Optional[str] = None   # named PolicyScna root-selection convention, if any
    adapter_version: Optional[str] = None         # third-party dependency adapter version, if any
    dependency_fingerprint: Optional[str] = None  # e.g. "pyxirr==0.10.8+<adapter_id>@<adapter_version>"
    warnings: List[str] = dataclasses.field(default_factory=list)
    limitations: List[str] = dataclasses.field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.calculator_id}:v{self.calculator_version}"


@dataclasses.dataclass(frozen=True)
class CashFlow:
    """
    A single dated cash flow, as required by section 7 of
    LIFE-PROTOTYPE-003. `cash_flow_id` is always derived deterministically
    from content (date, amount, original sequence) -- never random --
    since it can end up inside deterministically-hashed trace content.
    `sequence` preserves the position in the *original* input list purely
    for provenance; it never determines canonical (date-sorted) output
    order.
    """

    cash_flow_id: str
    date: str            # normalized ISO-8601 (YYYY-MM-DD)
    amount: str           # decimal-safe canonical string; sign preserved
    currency: str          # normalized uppercase
    source_type: str        # e.g. "premium", "withdrawal", "maturity_value"
    source_reference: Optional[str]
    description: Optional[str]
    sequence: int


CASH_FLOW_FIELD_ORDER = [
    "cash_flow_id", "date", "amount", "currency", "source_type",
    "source_reference", "description", "sequence",
]


@dataclasses.dataclass(frozen=True)
class DuplicateDateOperation:
    """
    Records one same-date netting operation performed under the
    NET_SAME_DATE policy. Always retained in the trace even when the net
    amount is exactly zero -- netting is never silently invisible.
    """

    date: str
    original_cash_flow_ids: List[str]
    original_amounts: List[str]
    net_amount: str
    note: str


DUPLICATE_DATE_OPERATION_FIELD_ORDER = [
    "date", "original_cash_flow_ids", "original_amounts", "net_amount", "note",
]


@dataclasses.dataclass(frozen=True)
class CalculationRequest:
    """
    A caller's request to run one registered calculator. `request_id` and
    `idempotency_key` are caller-supplied (never generated by the
    runtime) so that nothing in the pipeline introduces a random value
    that would make repeated execution non-reproducible.

    `cash_flows`, `day_count_convention`, and `duplicate_date_policy` are
    new in LIFE-PROTOTYPE-003, added at the end with defaults of `None`
    so every pre-existing (Prototype 002) request remains valid without
    them.
    """

    request_id: str
    calculator_id: str
    calculator_version: int
    calculation_date: str  # ISO-8601 date, e.g. "2026-07-26"
    input_values: Dict[str, object]   # raw values as given (str/int only -- see normalization.py)
    input_units: Dict[str, str]       # e.g. {"periodic_rate": "percentage"}
    currency: Optional[str]
    method: Optional[str]             # convention/method selection, where applicable
    source_observation_refs: List[str]
    assumption_refs: List[str]
    requested_rounding: Optional[Dict[str, object]]
    idempotency_key: str
    cash_flows: Optional[List[dict]] = None            # raw dated cash-flow list, if applicable
    day_count_convention: Optional[str] = None
    duplicate_date_policy: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class NormalizedInput:
    field_name: str
    original_value: str   # string form of exactly what was given
    original_unit: Optional[str]
    normalized_value: str  # decimal-safe canonical string (or "true"/"false" for flags)
    normalized_unit: str   # canonical unit after normalization, e.g. "decimal_fraction"


@dataclasses.dataclass(frozen=True)
class CalculationStep:
    step_number: int
    description: str
    expression: str        # substituted, human-readable expression, e.g. "100000 * (1.08)^10"
    unrounded_value: str    # full-precision Decimal string result of this step


@dataclasses.dataclass(frozen=True)
class CalculationTrace:
    """
    Contains everything required to reproduce the result. Never contains
    executable code -- `expression` fields in steps are display strings,
    not anything eval()'d by any consumer.

    `calculation_date`, `currency`, and `method` are included here even
    though they are not literally listed among the assignment's minimum
    trace fields: `input_hash` is derived from them (see canonical.py),
    so omitting them would silently break the trace's own stated promise
    to "contain everything required to reproduce the result" -- a
    validator could not actually recompute `input_hash` from the trace
    alone without them.

    `dated_cash_flow_context` is new in LIFE-PROTOTYPE-003: rather than
    adding ~15 separate top-level fields for original/normalized cash
    flows, duplicate-date operations, day-count convention, solver
    identity, root candidates, root status, convergence info, tolerance,
    and the XNPV consistency check (all of section 14's required trace
    additions), they are grouped under this single namespaced dict. This
    keeps the dataclass's core shape stable for every non-dated
    calculator (which simply leaves this field `None`) while still
    containing every item section 14 requires for the calculators that
    do use it. See CALCULATOR_ARCHITECTURE.md for the full sub-schema.
    """

    trace_id: str
    request_id: str
    calculator_id: str
    calculator_version: int
    formula_id: str
    calculation_date: str
    currency: Optional[str]
    method: Optional[str]
    normalized_inputs: List[NormalizedInput]
    steps: List[CalculationStep]
    output_before_rounding: Dict[str, str]
    output_after_rounding: Dict[str, str]
    rounding_applied: Dict[str, object]
    warnings: List[str]
    implementation_adapter_id: str
    implementation_version: str
    dependency_versions: Dict[str, str]
    input_hash: str
    output_hash: str
    dated_cash_flow_context: Optional[dict] = None


@dataclasses.dataclass(frozen=True)
class CalculationResult:
    """
    `root_status` and `dated_cash_flow_summary` are new in
    LIFE-PROTOTYPE-003. `root_status` is populated for XIRR_DATED/
    IRR_PERIODIC on SUCCESS *and* on the FAILED_CLOSED case where the
    cash-flow sign pattern itself is the problem (`INVALID_CASH_FLOWS`)
    -- this is metadata about *why* a computation could or couldn't
    proceed, not a plausible numeric result, so it is safe to populate
    even on failure. `dated_cash_flow_summary` (day_count_convention,
    duplicate_date_policy) is populated only on SUCCESS.
    """

    result_id: str
    request_id: str
    calculator_id: str
    calculator_version: int
    status: str  # one of RESULT_STATUS_*
    reason: Optional[str]  # machine-readable reason code, populated for any non-SUCCESS status
    output_values: Optional[Dict[str, str]]   # None unless status == SUCCESS
    output_units: Optional[Dict[str, str]]    # None unless status == SUCCESS
    rounding: Optional[Dict[str, object]]
    warnings: List[str]
    limitations: List[str]
    trace_id: Optional[str]  # None unless status == SUCCESS
    deterministic_input_hash: Optional[str]
    deterministic_output_hash: Optional[str]  # None unless status == SUCCESS
    root_status: Optional[str] = None
    dated_cash_flow_summary: Optional[dict] = None


@dataclasses.dataclass(frozen=True)
class CalculationValidationResult:
    validation_id: str
    result_id: str
    trace_id: Optional[str]
    checks: Dict[str, bool]
    overall_status: str  # "valid" | "invalid"
    reasons: List[str]


# --- Fixed field orders for canonical serialization -------------------------

NORMALIZED_INPUT_FIELD_ORDER = ["field_name", "original_value", "original_unit", "normalized_value", "normalized_unit"]
CALCULATION_STEP_FIELD_ORDER = ["step_number", "description", "expression", "unrounded_value"]

CALCULATION_TRACE_FIELD_ORDER = [
    "trace_id", "request_id", "calculator_id", "calculator_version", "formula_id",
    "calculation_date", "currency", "method",
    "normalized_inputs", "steps", "output_before_rounding", "output_after_rounding",
    "rounding_applied", "warnings", "implementation_adapter_id", "implementation_version",
    "dependency_versions", "input_hash", "output_hash", "dated_cash_flow_context",
]

CALCULATION_RESULT_FIELD_ORDER = [
    "result_id", "request_id", "calculator_id", "calculator_version", "status", "reason",
    "output_values", "output_units", "rounding", "warnings", "limitations", "trace_id",
    "deterministic_input_hash", "deterministic_output_hash", "root_status", "dated_cash_flow_summary",
]
