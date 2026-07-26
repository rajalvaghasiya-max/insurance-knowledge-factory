"""
life_intelligence_lab.calculators.registry
=============================================

The in-memory registry of CalculatorDefinition records. This is the
ONLY place a formula legitimately exists in this runtime -- the
orchestrator (`runtime.py`) may only ever look up an already-registered
(calculator_id, calculator_version) pair here; it can never construct a
CalculatorDefinition from request content, and no request field can add,
replace, or modify an entry.

Includes one deliberately RETIRED entry (`FV_LUMP_SUM:v0`, superseded by
`FV_LUMP_SUM:v1`) purely so the "retired calculator rejected for new
execution" behaviour has something real to test against -- it was never
otherwise used.
"""

from __future__ import annotations

from typing import Dict, Optional

from life_intelligence_lab.calculators.contracts import (
    CALCULATOR_STATUS_ACTIVE,
    CALCULATOR_STATUS_RETIRED,
    DAY_COUNT_ACT_365,
    DUPLICATE_DATE_POLICY_NET,
    DUPLICATE_DATE_POLICY_REJECT,
    CalculatorDefinition,
    FIELD_KIND_COUNT,
    FIELD_KIND_DECIMAL,
    FIELD_KIND_DECIMAL_LIST,
    FIELD_KIND_FLAG,
    FIELD_KIND_MONEY,
    FIELD_KIND_RATE,
    FIELD_KIND_STRING,
)
from life_intelligence_lab.calculators.adapters.pyxirr_adapter import (
    ADAPTER_VERSION as PYXIRR_ADAPTER_VERSION,
    dependency_fingerprint as pyxirr_dependency_fingerprint,
)

_MONEY_ROUNDING = {"money_decimal_places": 2, "mode": "ROUND_HALF_UP"}
_RATE_ROUNDING = {
    "rate_fraction_decimal_places": 6,
    "rate_percentage_decimal_places": 4,
    "mode": "ROUND_HALF_UP",
}
_STANDARD_LIMITATIONS = [
    "This is a mathematical projection based on the inputs and assumptions provided; it is "
    "not a guarantee of any future outcome."
]

_CALCULATORS: Dict[str, CalculatorDefinition] = {}


def _register(defn: CalculatorDefinition) -> None:
    _CALCULATORS[defn.key] = defn


_register(CalculatorDefinition(
    calculator_id="FV_LUMP_SUM",
    calculator_version=0,
    display_name="Future Value of a Lump Sum (retired)",
    formula_id="FV_LUMP_SUM_FORMULA_V0",
    formula_description="FV = PV * (1 + r)^n [retired prototype version, replaced by v1]",
    required_input_schema={
        "present_value": {"kind": FIELD_KIND_MONEY, "required": True},
        "periodic_rate": {"kind": FIELD_KIND_RATE, "required": True},
        "periods": {"kind": FIELD_KIND_COUNT, "required": True, "min": 0},
    },
    output_schema={"future_value": "money"},
    supported_units=["decimal", "percentage"],
    supported_methods=[],
    compounding_convention="annual, discrete compounding",
    timing_convention="n/a (single-point valuation)",
    rounding_policy=_MONEY_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.fv",
    status=CALCULATOR_STATUS_RETIRED,
    requires_currency=True,
    supersedes=None,
    warnings=["Retired. Use FV_LUMP_SUM:v1 instead."],
    limitations=_STANDARD_LIMITATIONS,
))

_register(CalculatorDefinition(
    calculator_id="FV_LUMP_SUM",
    calculator_version=1,
    display_name="Future Value of a Lump Sum",
    formula_id="FV_LUMP_SUM_FORMULA_V1",
    formula_description="FV = PV * (1 + r)^n",
    required_input_schema={
        "present_value": {"kind": FIELD_KIND_MONEY, "required": True},
        "periodic_rate": {"kind": FIELD_KIND_RATE, "required": True},
        "periods": {"kind": FIELD_KIND_COUNT, "required": True, "min": 0},
    },
    output_schema={"future_value": "money"},
    supported_units=["decimal", "percentage"],
    supported_methods=[],
    compounding_convention="annual, discrete compounding",
    timing_convention="n/a (single-point valuation)",
    rounding_policy=_MONEY_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.fv",
    status=CALCULATOR_STATUS_ACTIVE,
    requires_currency=True,
    supersedes="FV_LUMP_SUM:v0",
    warnings=[],
    limitations=_STANDARD_LIMITATIONS,
))

_register(CalculatorDefinition(
    calculator_id="PV_LUMP_SUM",
    calculator_version=1,
    display_name="Present Value of a Future Lump Sum",
    formula_id="PV_LUMP_SUM_FORMULA_V1",
    formula_description="PV = FV / (1 + r)^n",
    required_input_schema={
        "future_value": {"kind": FIELD_KIND_MONEY, "required": True},
        "periodic_rate": {"kind": FIELD_KIND_RATE, "required": True},
        "periods": {"kind": FIELD_KIND_COUNT, "required": True, "min": 0},
    },
    output_schema={"present_value": "money"},
    supported_units=["decimal", "percentage"],
    supported_methods=[],
    compounding_convention="annual, discrete compounding",
    timing_convention="n/a (single-point valuation)",
    rounding_policy=_MONEY_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.pv",
    status=CALCULATOR_STATUS_ACTIVE,
    requires_currency=True,
    supersedes=None,
    warnings=[],
    limitations=_STANDARD_LIMITATIONS,
))

_register(CalculatorDefinition(
    calculator_id="CAGR",
    calculator_version=1,
    display_name="Compound Annual Growth Rate",
    formula_id="CAGR_FORMULA_V1",
    formula_description="CAGR = (ending_value / beginning_value)^(1/n) - 1",
    required_input_schema={
        "beginning_value": {"kind": FIELD_KIND_DECIMAL, "required": True, "allow_negative": True},
        "ending_value": {"kind": FIELD_KIND_DECIMAL, "required": True, "allow_negative": True},
        "periods": {"kind": FIELD_KIND_COUNT, "required": True, "min": 0},
        "allow_negative_values": {"kind": FIELD_KIND_FLAG, "required": False, "default": "false"},
    },
    output_schema={"cagr": "decimal", "cagr_percentage": "decimal"},
    supported_units=["decimal", "percentage"],
    supported_methods=[],
    compounding_convention="annualized (implied by the (1/n) exponent)",
    timing_convention="n/a (single-point-to-single-point valuation)",
    rounding_policy=_RATE_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.cagr",
    status=CALCULATOR_STATUS_ACTIVE,
    supersedes=None,
    warnings=[],
    limitations=_STANDARD_LIMITATIONS + [
        "CAGR requires beginning_value != 0 and periods > 0; negative beginning/ending values "
        "are rejected by default and require an explicit allow_negative_values=true."
    ],
))

_register(CalculatorDefinition(
    calculator_id="INFLATION_ADJUSTED_FV",
    calculator_version=1,
    display_name="Inflation-Adjusted (Real) Future Value — Exact",
    formula_id="INFLATION_ADJUSTED_FV_FORMULA_V1",
    formula_description=(
        "Method 'deflate_nominal': real_FV = [PV*(1+nominal)^n] / (1+inflation)^n. "
        "Method 'exact_real_rate': real_rate = (1+nominal)/(1+inflation)-1; real_FV = PV*(1+real_rate)^n. "
        "Both are the exact Fisher relationship and agree to within Decimal rounding."
    ),
    required_input_schema={
        "present_value": {"kind": FIELD_KIND_MONEY, "required": True},
        "nominal_rate": {"kind": FIELD_KIND_RATE, "required": True},
        "inflation_rate": {"kind": FIELD_KIND_RATE, "required": True},
        "periods": {"kind": FIELD_KIND_COUNT, "required": True, "min": 0},
    },
    output_schema={"real_future_value": "money"},
    supported_units=["decimal", "percentage"],
    supported_methods=["deflate_nominal", "exact_real_rate"],
    compounding_convention="annual, discrete compounding",
    timing_convention="n/a (single-point valuation)",
    rounding_policy=_MONEY_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.inflation_adjusted",
    status=CALCULATOR_STATUS_ACTIVE,
    requires_currency=True,
    supersedes=None,
    warnings=[],
    limitations=_STANDARD_LIMITATIONS + [
        "'method' must be explicitly specified as one of ['deflate_nominal', 'exact_real_rate']; "
        "there is no default."
    ],
))

_register(CalculatorDefinition(
    calculator_id="INFLATION_ADJUSTED_FV_APPROX",
    calculator_version=1,
    display_name="Inflation-Adjusted (Real) Future Value — Approximate",
    formula_id="INFLATION_ADJUSTED_FV_APPROX_FORMULA_V1",
    formula_description="approximate_real_rate = nominal_rate - inflation_rate; real_FV = PV*(1+approx_real_rate)^n",
    required_input_schema={
        "present_value": {"kind": FIELD_KIND_MONEY, "required": True},
        "nominal_rate": {"kind": FIELD_KIND_RATE, "required": True},
        "inflation_rate": {"kind": FIELD_KIND_RATE, "required": True},
        "periods": {"kind": FIELD_KIND_COUNT, "required": True, "min": 0},
    },
    output_schema={"real_future_value": "money"},
    supported_units=["decimal", "percentage"],
    supported_methods=[],
    compounding_convention="annual, discrete compounding",
    timing_convention="n/a (single-point valuation)",
    rounding_policy=_MONEY_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.inflation_adjusted_approx",
    status=CALCULATOR_STATUS_ACTIVE,
    requires_currency=True,
    supersedes=None,
    warnings=[
        "APPROXIMATE METHOD: not the exact Fisher relationship. Diverges from "
        "INFLATION_ADJUSTED_FV, increasingly so at higher rates or longer horizons."
    ],
    limitations=_STANDARD_LIMITATIONS,
))

# --- LIFE-PROTOTYPE-003: dated and periodic cash-flow calculators ----------

_DATED_CASH_FLOW_ROUNDING = {
    "rate_decimal_places": 6, "rate_percentage_decimal_places": 4, "mode": "ROUND_HALF_UP",
}
_ROOT_HANDLING_POLICY = (
    "PolicyScna candidate-root policy v1: chronological sign changes are counted after "
    "normalization; exactly one sign change is reported as root_status=SINGLE_ROOT, more than "
    "one as root_status=MULTIPLE_ROOTS_POSSIBLE (candidate only, never presented as uniquely "
    "correct). The candidate rate itself is whatever the pinned pyxirr version's solver "
    "returns -- this policy governs how that candidate is LABELLED, not how it is computed."
)
_DEPENDENCY_FINGERPRINT = pyxirr_dependency_fingerprint()

_register(CalculatorDefinition(
    calculator_id="XIRR_DATED",
    calculator_version=1,
    display_name="XIRR — Internal Rate of Return for Dated Cash Flows",
    formula_id="XIRR_DATED_FORMULA_V1",
    formula_description="Solves XNPV(r) = 0 for irregular, dated cash flows via the contained PyXirrAdapter.",
    required_input_schema={
        "day_count_convention": {"kind": FIELD_KIND_STRING, "required": True, "allowed_values": (DAY_COUNT_ACT_365,)},
        "duplicate_date_policy": {
            "kind": FIELD_KIND_STRING, "required": True,
            "allowed_values": (DUPLICATE_DATE_POLICY_REJECT, DUPLICATE_DATE_POLICY_NET),
        },
    },
    output_schema={"rate": "decimal", "rate_percentage": "decimal"},
    supported_units=[],
    supported_methods=[],
    compounding_convention="annualized effective rate implied by ACT_365 year fractions",
    timing_convention="irregular, dated cash flows",
    rounding_policy=_DATED_CASH_FLOW_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.xirr",
    status=CALCULATOR_STATUS_ACTIVE,
    requires_currency=False,
    requires_cash_flows=True,
    supersedes=None,
    supported_day_count_conventions=[DAY_COUNT_ACT_365],
    supported_duplicate_date_policies=[DUPLICATE_DATE_POLICY_REJECT, DUPLICATE_DATE_POLICY_NET],
    root_handling_policy=_ROOT_HANDLING_POLICY,
    adapter_version=PYXIRR_ADAPTER_VERSION,
    dependency_fingerprint=_DEPENDENCY_FINGERPRINT,
    warnings=[],
    limitations=_STANDARD_LIMITATIONS + [
        "Only the ACT_365 day-count convention is currently supported.",
        "When root_status is MULTIPLE_ROOTS_POSSIBLE, the returned rate is a candidate only, "
        "not guaranteed to be uniquely or economically correct.",
    ],
))

_register(CalculatorDefinition(
    calculator_id="XNPV_DATED",
    calculator_version=1,
    display_name="XNPV — Net Present Value for Dated Cash Flows",
    formula_id="XNPV_DATED_FORMULA_V1",
    formula_description="XNPV(r) = sum_i CF_i / (1+r)^year_fraction(d0,di), evaluated via the contained PyXirrAdapter.",
    required_input_schema={
        "rate": {"kind": FIELD_KIND_RATE, "required": True},
        "day_count_convention": {"kind": FIELD_KIND_STRING, "required": True, "allowed_values": (DAY_COUNT_ACT_365,)},
        "duplicate_date_policy": {
            "kind": FIELD_KIND_STRING, "required": True,
            "allowed_values": (DUPLICATE_DATE_POLICY_REJECT, DUPLICATE_DATE_POLICY_NET),
        },
    },
    output_schema={"xnpv": "money"},
    supported_units=["decimal", "percentage"],
    supported_methods=[],
    compounding_convention="ACT_365 year-fraction discounting",
    timing_convention="irregular, dated cash flows",
    rounding_policy=_MONEY_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.xnpv",
    status=CALCULATOR_STATUS_ACTIVE,
    requires_currency=False,
    requires_cash_flows=True,
    supersedes=None,
    supported_day_count_conventions=[DAY_COUNT_ACT_365],
    supported_duplicate_date_policies=[DUPLICATE_DATE_POLICY_REJECT, DUPLICATE_DATE_POLICY_NET],
    root_handling_policy=None,  # XNPV evaluates at a given rate; it does not solve for a root
    adapter_version=PYXIRR_ADAPTER_VERSION,
    dependency_fingerprint=_DEPENDENCY_FINGERPRINT,
    warnings=[],
    limitations=_STANDARD_LIMITATIONS + ["Only the ACT_365 day-count convention is currently supported."],
))

_register(CalculatorDefinition(
    calculator_id="IRR_PERIODIC",
    calculator_version=1,
    display_name="Periodic Internal Rate of Return",
    formula_id="IRR_PERIODIC_FORMULA_V1",
    formula_description="Solves for r such that sum_i CF_i / (1+r)^i = 0 over regular, undated periods.",
    required_input_schema={
        "cash_flows": {"kind": FIELD_KIND_DECIMAL_LIST, "required": True},
    },
    output_schema={"rate": "decimal", "rate_percentage": "decimal"},
    supported_units=[],
    supported_methods=[],
    compounding_convention="regular periodic compounding (period length undated/implicit)",
    timing_convention="regular, undated periods indexed 0..n-1",
    rounding_policy=_DATED_CASH_FLOW_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.irr_periodic",
    status=CALCULATOR_STATUS_ACTIVE,
    requires_currency=False,
    requires_cash_flows=False,
    supersedes=None,
    supported_day_count_conventions=[],
    supported_duplicate_date_policies=[],
    root_handling_policy=_ROOT_HANDLING_POLICY,
    adapter_version=PYXIRR_ADAPTER_VERSION,
    dependency_fingerprint=_DEPENDENCY_FINGERPRINT,
    warnings=[],
    limitations=_STANDARD_LIMITATIONS + [
        "Deliberately separate from XIRR_DATED: no dates, no day-count convention. Do not "
        "conflate periodic IRR with dated XIRR."
    ],
))

_register(CalculatorDefinition(
    calculator_id="NPV_PERIODIC",
    calculator_version=1,
    display_name="Periodic Net Present Value",
    formula_id="NPV_PERIODIC_FORMULA_V1",
    formula_description="NPV(r) = sum_i CF_i / (1+r)^i over regular, undated periods.",
    required_input_schema={
        "rate": {"kind": FIELD_KIND_RATE, "required": True},
        "cash_flows": {"kind": FIELD_KIND_DECIMAL_LIST, "required": True},
    },
    output_schema={"npv": "money"},
    supported_units=["decimal", "percentage"],
    supported_methods=[],
    compounding_convention="regular periodic compounding (period length undated/implicit)",
    timing_convention="regular, undated periods indexed 0..n-1",
    rounding_policy=_MONEY_ROUNDING,
    implementation_adapter_id="life_intelligence_lab.calculators.formulas.npv_periodic",
    status=CALCULATOR_STATUS_ACTIVE,
    requires_currency=True,
    requires_cash_flows=False,
    supersedes=None,
    supported_day_count_conventions=[],
    supported_duplicate_date_policies=[],
    root_handling_policy=None,
    adapter_version=PYXIRR_ADAPTER_VERSION,
    dependency_fingerprint=_DEPENDENCY_FINGERPRINT,
    warnings=[],
    limitations=_STANDARD_LIMITATIONS + [
        "Deliberately separate from XNPV_DATED: no dates, no day-count convention."
    ],
))


def get(calculator_id: str, calculator_version: int) -> Optional[CalculatorDefinition]:
    return _CALCULATORS.get(f"{calculator_id}:v{calculator_version}")


def exists_with_any_version(calculator_id: str) -> bool:
    return any(defn.calculator_id == calculator_id for defn in _CALCULATORS.values())


def all_definitions() -> Dict[str, CalculatorDefinition]:
    return dict(_CALCULATORS)
