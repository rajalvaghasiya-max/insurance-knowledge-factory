# Phase 2 — Governed Coverage & Readiness Alignment Gate

**Status:** ACTIVE — REPORTING SEPARATION PROVEN; ASSESSMENT CONTRACT INTEGRATION PENDING  
**Date:** 2026-08-15

## Purpose

Separate legacy product-intelligence field coverage from governed/current/publication readiness so repository reporting cannot imply that field presence means PolicyScna may safely use or publish a product fact.

This is an observability/governance correction. It is not a new extractor, publication engine, recommendation feature, or product onboarding project.

## Defect under pressure

`scripts/audit_product_coverage.py` historically scored presence in `knowledge/health/<insurer>/<product>/intelligence/product_intelligence.json` and mapped high presence to labels such as `READY`.

`scripts/audit_portfolio_coverage.py` then aggregated those labels and could recommend advisor-facing/comparison use.

Those metrics do not establish:

- current governed source authority;
- reviewed currentness;
- semantic review completeness;
- applicability resolution;
- publication eligibility;
- publication state;
- absence of unresolved residue.

Therefore historical/intelligence completeness and governed readiness are now separate dimensions.

## Backward-compatibility rule

The existing `overall_coverage`, `coverage_status`, section coverage, quality fields, and missing-field metrics remain available as **legacy intelligence coverage** so historical tooling/tests are not silently broken.

Their meaning is explicit:

```text
legacy intelligence coverage != governed readiness != publication state
```

Product reports now identify:

```text
coverage_semantics = LEGACY_INTELLIGENCE_FIELD_PRESENCE
```

## Governed-readiness reporting boundary

Product reports carry a separate `governed_readiness` block.

When no governed readiness assessment has been materialized, the only safe state is:

```text
status = NOT_ASSESSED
```

The product coverage auditor does not derive governed readiness from legacy field presence or validator score.

The portfolio auditor aggregates legacy coverage and governed readiness separately and does not translate legacy percentages into governed-readiness percentages/statuses.

## Real-product verification

Focused reporting regressions:

```text
11 passed
```

The regenerated current reports produced:

### Star Comprehensive

```text
Legacy coverage        : 100.0%
Legacy coverage status : READY
Governed readiness     : NOT_ASSESSED
Quality                 : PASS / 100
```

This is the intended result. `READY` remains only the backward-compatible legacy intelligence-presence label and does not establish current governed or publication readiness.

### Aditya Birla Activ One

```text
Legacy coverage        : 83.07%
Legacy coverage status : USABLE_WITH_REVIEW
Governed readiness     : NOT_ASSESSED
Quality                 : REVIEW_REQUIRED / 85
```

The legacy report still lists waiting-period field presence, but that does not override the current governed waiting-period pressure result where PED numeric duration remains unresolved without schedule/table binding.

### Health portfolio

```text
Products                         : 2
Average legacy coverage          : 91.53%
Legacy READY                     : 1
Legacy USABLE_WITH_REVIEW        : 1
Governed readiness NOT_ASSESSED  : 2
```

Both products remain in the attention list because neither has a materialized governed-readiness assessment. Strong legacy coverage therefore no longer causes portfolio reporting to imply governed readiness.

## Governed-readiness assessment contract

A generic assessment contract now defines independent dimensions:

- source governance/currentness;
- semantic review;
- applicability;
- publication eligibility;
- publication state;
- unresolved residue;
- evidence references.

The assessment summary status is **derived**, never asserted directly in JSON.

A materialized assessment cannot write its own `status = READY` or `status = PUBLISHED`. Generic code derives one of:

```text
NOT_ASSESSED
BLOCKED
REVIEW_REQUIRED
READY_FOR_PUBLICATION_REVIEW
PUBLISHED
```

Key fail-closed rules include:

- assessed states require at least one evidence reference;
- currentness unresolved/historical-only, semantic conflict, unresolved applicability, or ineligibility derive `BLOCKED`;
- unresolved residue prevents a ready state;
- `PUBLISHED` is invalid unless source governance, semantic review, applicability, publication eligibility, and residue are fully resolved;
- entity mismatch and unknown fields fail closed.

This contract does not itself decide that Star or Activ One is ready. Product assessments must be materialized from existing governed evidence under review.

## Portfolio rule

Portfolio reporting must aggregate legacy coverage and governed readiness separately. It must never average or translate legacy coverage percentages into governed-readiness percentages/statuses.

## Guardrails

- Do not delete or reinterpret historical product-intelligence data.
- Do not mark a product publication-ready from coverage percentage.
- Do not infer currentness from file presence.
- Do not infer applicability from extraction completeness.
- Do not infer publication state from certification/review evidence.
- Preserve fail-closed behavior when governed readiness evidence is absent.
- Do not hand-author an overall readiness status; derive it from assessed dimensions.
- Do not manufacture assessments merely to improve portfolio metrics.
- No product-specific production reasoning.
- No frontend, Motor, Life, recommendation-productization, or DB migration scope.

## Acceptance criteria

1. Existing legacy coverage tests remain valid.
2. Product reports explicitly identify the legacy metric semantics.
3. Product reports expose a separate governed-readiness state.
4. Missing governed readiness yields `NOT_ASSESSED`, never `READY`.
5. Portfolio reports aggregate governed readiness separately.
6. Portfolio recommendations no longer imply governed/product publication readiness from legacy coverage alone.
7. Governed-readiness summary status is derived from evidence-backed independent dimensions.
8. Invalid/inconsistent assessments fail closed.
9. Relevant regressions remain green.

## Exit condition

Reporting separation is proven on real Star and Activ One reports. The remaining implementation step is to route materialized `governed_readiness.json` records through the generic assessment contract, then exercise at least one honest governed product assessment without resolving known residue by guesswork and close relevant regressions.