# MO-025 — Product-Benefit Discovery and Comparison Closure

## Status

**CLOSED**

## Certified branch

`feature/mo-025-benefit-discovery-comparison`

## Entry baseline

MO-025 was certified from the Health Generalization Pilot baseline, which had a clean full repository regression result of:

`2392 passed`

The MO-025 implementation itself was already present on that certified baseline. The purpose of this milestone step was therefore to re-audit, re-certify, and formally close the governed discovery/comparison path rather than duplicate previously implemented code.

## Certified capability path

The authoritative MO-025 path is:

`governed catalogue -> benefit discovery -> comparison eligibility -> mechanic normalization -> factual comparison -> comparison orchestration -> explanation projection -> governed pre-ranking handoff`

The certified active components are:

- `insurance_intelligence/benefits/catalogue.py`
- `insurance_intelligence/benefits/registry.py`
- `insurance_intelligence/benefits/discovery.py`
- `insurance_intelligence/benefits/eligibility.py`
- `insurance_intelligence/benefits/normalization.py`
- `insurance_intelligence/benefits/comparison.py`
- `insurance_intelligence/benefits/orchestration.py`
- `insurance_intelligence/benefits/explanation_projection.py`
- `insurance_intelligence/benefits/governed_handoff.py`

## Current governed comparison pilot

The certified comparison pair is:

- Star Health — Star Comprehensive — Automatic Restoration of Sum Insured
- Aditya Birla Health — Activ One NXT — Super Reload

Both implementations resolve to the canonical concept:

`health:coverage_capacity:restoration_benefit`

## Certified behavior

MO-025 certifies that the system can:

1. discover only active, approved, published product-benefit implementations for a governed canonical concept and effective date;
2. preserve insurer, product, variant, implementation, mechanic, and evidence identities;
3. determine whether two implementations are fully, partially, or not eligible for comparison;
4. normalize representation differences without mutating source-backed governed records;
5. produce deterministic factual comparisons with shared, different, blocked, left-only, and right-only dimensions;
6. preserve source mechanic identities and evidence lineage through normalized comparison;
7. orchestrate discovery, eligibility, normalization, and comparison with explicit blocked or partial outcomes;
8. project the comparison into a presentation-safe structured payload;
9. permit only the exact governed comparison projection to cross the pre-ranking handoff.

## Scope boundary

MO-025 does **not**:

- rank products;
- select a winner;
- recommend a product;
- infer customer suitability;
- determine entitlement;
- predict or guarantee claim payment;
- assess a claim;
- generate ungoverned free-form comparative advice.

Those boundaries are deliberate. Ranking belongs to MO-026 and suitability/recommendation belongs to MO-027.

## Certification evidence

Current-baseline certification test:

`tests/insurance_intelligence/test_mo025_current_baseline_certification.py`

Focused MO-025 certification suite result:

`137 passed`

The focused suite covered:

- benefit discovery;
- comparison eligibility;
- mechanic normalization;
- normalized benefit comparison;
- governed comparison orchestration;
- governed comparison explanation projection;
- pre-ranking hardening;
- end-to-end current-baseline MO-025 certification.

## Historical implementation lineage

The earlier MO-025 implementation sequence consisted of:

- MO-025E — governed benefit discovery;
- MO-025F — comparison eligibility gate;
- MO-025G — comparison mechanic normalization;
- MO-025H — normalized factual comparison;
- MO-025I — governed comparison orchestration;
- MO-025J — comparison explanation projection;
- pre-ranking hardening and governed handoff.

These components have now been re-certified on the current authoritative baseline rather than assumed valid because of historical milestone test results.

## Remaining known defect

The previously deferred legal-condition defect involving some `unless` / `except` exception constructions remains open outside this restoration comparison path. It does not invalidate this MO-025 closure, but it remains a blocker before broad certification of additional legal-condition rule families that depend on those constructions.

## Closure decision

MO-025 is **CLOSED**.

The next roadmap milestone is:

**MO-026 — Explainable Ranking Engine**

MO-026 must consume only `GovernedComparisonHandoff` and must not reconstruct comparison facts directly from raw documents, historical comparison outputs, or ungoverned product records.
