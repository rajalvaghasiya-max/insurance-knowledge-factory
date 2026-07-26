"""
life_intelligence_lab.calculators.rounding
=============================================

Rounding policy for the TVM calculator runtime.

Defaults (documented here as the single source of truth):
  - Monetary display: 2 decimal places, ROUND_HALF_UP.
  - Rate display (decimal fraction, e.g. 0.122462): 6 decimal places,
    ROUND_HALF_UP. This gives ~0.0001 percentage-point display precision.
  - Rate display (percentage convenience form, e.g. 12.2462): 4 decimal
    places, ROUND_HALF_UP -- chosen so that a 6dp decimal-fraction and a
    4dp percentage figure represent the same underlying precision.

Rounding is applied ONLY at the final output boundary. Every intermediate
value throughout a calculation stays a full-precision Decimal until the
single rounding step at the end -- calculators must not round at every
step unless a calculator definition explicitly requires it (none do, in
this prototype).
"""

from decimal import ROUND_HALF_UP, Decimal

DEFAULT_MONEY_DECIMAL_PLACES = 2
DEFAULT_RATE_DECIMAL_PLACES = 6
DEFAULT_RATE_PERCENTAGE_DECIMAL_PLACES = 4
ROUNDING_MODE = ROUND_HALF_UP


def round_money(value: Decimal, decimal_places: int = DEFAULT_MONEY_DECIMAL_PLACES) -> Decimal:
    quantum = Decimal(1).scaleb(-decimal_places)
    rounded = value.quantize(quantum, rounding=ROUNDING_MODE)
    # Decimal distinguishes -0 from +0; a tiny negative residual (e.g. from
    # an XNPV consistency check at a solved root) can legitimately round to
    # "-0.00", which is confusing noise for a money display, not meaningful
    # information -- normalize it to positive zero.
    return abs(rounded) if rounded == 0 else rounded


def round_rate_fraction(value: Decimal, decimal_places: int = DEFAULT_RATE_DECIMAL_PLACES) -> Decimal:
    quantum = Decimal(1).scaleb(-decimal_places)
    rounded = value.quantize(quantum, rounding=ROUNDING_MODE)
    return abs(rounded) if rounded == 0 else rounded


def round_rate_percentage(value: Decimal, decimal_places: int = DEFAULT_RATE_PERCENTAGE_DECIMAL_PLACES) -> Decimal:
    quantum = Decimal(1).scaleb(-decimal_places)
    rounded = value.quantize(quantum, rounding=ROUNDING_MODE)
    return abs(rounded) if rounded == 0 else rounded
