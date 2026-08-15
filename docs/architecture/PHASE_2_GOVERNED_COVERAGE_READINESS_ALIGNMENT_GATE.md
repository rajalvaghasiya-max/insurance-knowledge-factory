# Phase 2 — Governed Coverage & Readiness Alignment Gate

**Status:** ACTIVE — REPORTING-SEMANTICS ALIGNMENT STARTED  
**Date:** 2026-08-15

## Purpose

Separate legacy product-intelligence field coverage from governed/current/publication readiness so repository reporting cannot imply that field presence means PolicyScna may safely use or publish a product fact.

This is an observability/governance correction. It is not a new extractor, publication engine, recommendation feature, or product onboarding project.

## Defect under pressure

`scripts/audit_product_coverage.py` currently scores presence in `knowledge/health/<insurer>/<product>/intelligence/product_intelligence.json` and maps high presence to labels such as `READY`.

`scripts/audit_portfolio_coverage.py` then aggregates those labels and may recommend advisor-facing/comparison use.

Those metrics do not establish:

- current governed source authority;
- reviewed currentness;
- semantic review completeness;
- applicability resolution;
- publication eligibility;
- publication state;
- absence of unresolved residue.

Therefore historical/intelligence completeness and governed readiness must be reported as separate dimensions.

## Backward-compatibility rule

The existing `overall_coverage`, `coverage_status`, section coverage, quality fields, and missing-field metrics remain available as **legacy intelligence coverage** so historical tooling/tests are not silently broken.

Their meaning must become explicit:

```text
legacy intelligence coverage != governed readiness != publication state
```

## Governed-readiness contract

Product reports will carry a separate `governed_readiness` block.

When no governed readiness assessment has been materialized, the only safe state is:

```text
status = NOT_ASSESSED
```

The product coverage auditor must not derive governed readiness from legacy field presence or validator score.

A future governed readiness assessment may report independent dimensions such as source governance/currentness, semantic review, applicability, publication eligibility, publication state, and unresolved residue, but those values must come from governed artifacts rather than heuristic inference.

## Portfolio rule

Portfolio reporting must aggregate legacy coverage and governed readiness separately. It must never average or translate legacy coverage percentages into governed-readiness percentages/statuses.

## Guardrails

- Do not delete or reinterpret historical product-intelligence data.
- Do not mark a product publication-ready from coverage percentage.
- Do not infer currentness from file presence.
- Do not infer applicability from extraction completeness.
- Do not infer publication state from certification/review evidence.
- Preserve fail-closed behavior when governed readiness evidence is absent.
- No product-specific production reasoning.
- No frontend, Motor, Life, recommendation-productization, or DB migration scope.

## Acceptance criteria

1. Existing legacy coverage tests remain valid.
2. Product reports explicitly identify the legacy metric semantics.
3. Product reports expose a separate governed-readiness state.
4. Missing governed readiness yields `NOT_ASSESSED`, never `READY`.
5. Portfolio reports aggregate governed readiness separately.
6. Portfolio recommendations no longer imply governed/product publication readiness from legacy coverage alone.
7. Relevant regressions remain green.

## Exit condition

This gate closes when legacy coverage and governed readiness are structurally distinct in product and portfolio reporting, absence of governed readiness evidence fails closed, and regression tests prove backward compatibility.