# Phase 2 — Governed Coverage & Readiness Alignment Gate

**Status:** ACTIVE — REPORTING + CONTRACT PROVEN; FIRST REAL PRODUCT ASSESSMENT MATERIALIZED  
**Date:** 2026-08-15

## Purpose

Separate legacy product-intelligence field coverage from governed/current/publication readiness so repository reporting cannot imply that field presence means PolicyScna may safely use or publish a product fact.

This is an observability/governance correction. It is not a new extractor, publication engine, recommendation feature, or product onboarding project.

## Defect under pressure

`scripts/audit_product_coverage.py` historically scored presence in `knowledge/health/<insurer>/<product>/intelligence/product_intelligence.json` and mapped high presence to labels such as `READY`.

`scripts/audit_portfolio_coverage.py` then aggregated those labels and could recommend advisor-facing/comparison use.

Those metrics do not establish current governed source authority, reviewed currentness, semantic review completeness, applicability resolution, publication eligibility, publication state, or absence of unresolved residue.

Therefore historical/intelligence completeness and governed readiness are separate dimensions.

## Backward-compatibility rule

The existing `overall_coverage`, `coverage_status`, section coverage, quality fields, and missing-field metrics remain available as **legacy intelligence coverage** so historical tooling/tests are not silently broken.

Their meaning is explicit:

```text
legacy intelligence coverage != governed readiness != publication state
```

Product reports identify:

```text
coverage_semantics = LEGACY_INTELLIGENCE_FIELD_PRESENCE
```

## Governed-readiness reporting boundary

Product reports carry a separate `governed_readiness` block. When no governed readiness assessment has been materialized, the only safe state is:

```text
status = NOT_ASSESSED
```

The product coverage auditor does not derive governed readiness from legacy field presence or validator score. The portfolio auditor aggregates legacy coverage and governed readiness separately and does not translate legacy percentages into governed-readiness percentages/statuses.

## Real-product reporting verification

Initial focused reporting regressions:

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

### Aditya Birla Activ One

```text
Legacy coverage        : 83.07%
Legacy coverage status : USABLE_WITH_REVIEW
Governed readiness     : NOT_ASSESSED
Quality                 : REVIEW_REQUIRED / 85
```

### Health portfolio

```text
Products                         : 2
Average legacy coverage          : 91.53%
Legacy READY                     : 1
Legacy USABLE_WITH_REVIEW        : 1
Governed readiness NOT_ASSESSED  : 2
```

Both products remained in the attention list because neither had a materialized governed-readiness assessment. Strong legacy coverage therefore no longer implied governed readiness.

## Governed-readiness assessment contract

A generic assessment contract defines independent dimensions:

- source governance/currentness;
- semantic review;
- applicability;
- publication eligibility;
- publication state;
- unresolved residue;
- evidence references.

The assessment summary status is **derived**, never asserted directly in JSON. A materialized assessment cannot write its own `status = READY` or `status = PUBLISHED`. Generic code derives one of:

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

The product auditor now routes materialized `governed_readiness.json` through this contract rather than trusting editable summary fields.

## Focused contract/integration regression closure

The complete governed-readiness focused set now passes:

```text
25 passed
```

Coverage:

- governed-readiness contract derivation and invalid-state behavior;
- product audit backward compatibility;
- product audit contract integration;
- portfolio readiness separation.

The test migration exposed several intentionally strict vocabulary/derivation rules (`CURRENT_GOVERNED`, `INELIGIBLE`, and `BLOCKED` for unresolved applicability/ineligibility). The contract was not weakened to satisfy stale fixtures; fixtures were corrected to model the intended states.

## First real governed product assessment — Star Comprehensive

Materialized:

```text
knowledge/health/star_health/star_comprehensive/governance/governed_readiness.json
```

Evidence supports the following conservative product-level dimensions:

```text
source_governance        = CURRENT_GOVERNED
semantic_review          = PARTIAL
applicability            = PARTIAL
publication_eligibility  = REVIEW_REQUIRED
publication_state        = NOT_PUBLISHED
```

Reasons:

- the governed Star policy wording is anchored to the registered current source SHA `b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f`;
- room-rent and bariatric rules have authoritative publications;
- conditional copayment remains explicitly withheld / bound-not-published;
- product-wide semantic review and applicability completeness are not established merely because selected consequential rules are certified;
- whole-product publication therefore must not be inferred from the existence of some authoritative rule publications.

Explicit unresolved residue:

```text
conditional_copayment_bound_not_published
product_level_semantic_review_not_complete
product_level_applicability_not_fully_resolved
```

The generic contract should therefore derive:

```text
REVIEW_REQUIRED
```

This is intentionally more conservative than legacy `coverage_status = READY` and demonstrates the purpose of the new separation.

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
- Whole-product readiness must not be inferred from publication of selected rules.
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
9. At least one real product assessment is materialized conservatively from repository evidence.
10. Relevant regressions remain green.

## Exit condition

Reporting separation, the generic assessment contract, and the first real Star assessment are now implemented. The remaining closure step is to regenerate Star and portfolio reports through the materialized assessment, verify that Star derives `REVIEW_REQUIRED` while Activ One remains `NOT_ASSESSED`, then run broader relevant regressions before certifying and freezing this gate.
