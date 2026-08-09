# CD-1 — Exception Semantics Hardening Closure

## Status

CLOSED

## Context

CD-1 tracked a known semantic defect in conditional co-payment parsing: exception phrases introduced by forms such as `unless` or `except` could be absorbed into the trigger clause instead of being represented separately. That defect was acceptable only while the certified Star pilot did not rely on those phrase families. It became a prerequisite for MO-026 protection-floor assessment because a trigger/exception merge could materially change the assessment of a financially important restriction.

## Change

The active deterministic conditional co-payment reasoning path now preserves three distinct semantics:

- trigger;
- exception;
- applicability scope.

`unless` and `except` forms terminate the trigger clause and begin a separate exception clause. Existing `does not apply / will not apply / shall not apply` forms remain supported. Unsupported exception signals continue to fail closed rather than being silently merged into another semantic field.

## Certified invariants

The focused certification verifies that:

1. `unless` does not remain inside the trigger;
2. `unless` is preserved as an explicit exception;
3. `except` / `except where` does not remain inside the trigger;
4. `except` semantics are preserved explicitly;
5. the existing Star Comprehensive canonical conditional co-payment regression remains unchanged;
6. the active reasoning rules still preserve deterministic outputs and evidence lineage;
7. the Star pilot remains stable;
8. the governed pre-ranking boundary remains stable.

## Validation

Focused regression result supplied from the active MO-026 branch:

- 77 passed

The suite covered:

- `tests/insurance_intelligence/test_cd1_exception_semantics_hardening.py`
- `tests/insurance_intelligence/test_reasoning_rules.py`
- `tests/insurance_intelligence/test_star_comprehensive_pilot.py`
- `tests/insurance_intelligence/test_pre_ranking_hardening.py`

## Architecture consequence

CD-1 is no longer a deferred rule-family risk for conditional co-payment semantics. MO-026 may now build a governed co-payment protection-floor assessment policy on top of structured percentage, trigger, exception, and scope semantics without carrying the known exception-merging defect forward.

No ranking, recommendation, customer suitability, claim entitlement, or monetary outcome logic was introduced by this hardening.
