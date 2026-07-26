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
    CalculatorDefinition,
    FIELD_KIND_COUNT,
    FIELD_KIND_DECIMAL,
    FIELD_KIND_FLAG,
    FIELD_KIND_MONEY,
    FIELD_KIND_RATE,
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


def get(calculator_id: str, calculator_version: int) -> Optional[CalculatorDefinition]:
    return _CALCULATORS.get(f"{calculator_id}:v{calculator_version}")


def exists_with_any_version(calculator_id: str) -> bool:
    return any(defn.calculator_id == calculator_id for defn in _CALCULATORS.values())


def all_definitions() -> Dict[str, CalculatorDefinition]:
    return dict(_CALCULATORS)
