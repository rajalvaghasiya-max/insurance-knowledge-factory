# Phase 2 — Governed Coverage & Readiness Alignment Gate

**Status:** CERTIFIED AND FROZEN  
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

The regenerated current reports initially produced:

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

The product auditor routes materialized `governed_readiness.json` through this contract rather than trusting editable summary fields.

## Focused contract/integration regression closure

The complete governed-readiness focused set passes:

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

The generic contract derives:

```text
REVIEW_REQUIRED
```

This is intentionally more conservative than legacy `coverage_status = READY` and demonstrates the purpose of the new separation.

## Real Star + portfolio derivation result

After materializing the Star assessment, the real product report produced:

```text
Star Comprehensive
Legacy coverage        : 100.0%
Legacy coverage status : READY
Governed readiness     : REVIEW_REQUIRED
Quality                 : PASS / 100
```

The Health portfolio then produced:

```text
Products                          : 2
Average legacy coverage           : 91.53%
Legacy READY                      : 1
Legacy USABLE_WITH_REVIEW         : 1
Governed readiness REVIEW_REQUIRED: 1
Governed readiness NOT_ASSESSED   : 1
```

Both products remain in the attention list:

- `star_health:star_comprehensive` because governed readiness is `REVIEW_REQUIRED` despite 100% legacy field coverage;
- `aditya_birla_health:activ_one` because governed readiness is still `NOT_ASSESSED`.

This is the intended observable distinction:

```text
Star legacy coverage READY
!=
Star governed readiness REVIEW_REQUIRED
```

The reporting system therefore no longer allows historical extraction completeness to masquerade as current governed or publication readiness.

## Final regression closure

Broader regression validation across the changed governance/reporting surfaces is green:

```text
tests/factory_core                                      : 139 passed
focused product/portfolio governed-readiness audit set : 14 passed
regressions                                             : 0
```

Together with the earlier focused governed-readiness contract/integration set:

```text
25 passed
```

No contract weakening, product-specific reasoning, publication shortcut, or readiness backfill was introduced to obtain closure.

## Certified architecture outcome

The approved reporting model is now:

```text
legacy intelligence coverage
!=
governed readiness
!=
publication state
```

Governed readiness is materialized only from explicit governed evidence and independent dimensions, and summary status is derived generically and fail-closed.

A product may therefore legitimately be:

```text
legacy coverage READY
+
governed readiness REVIEW_REQUIRED
```

without contradiction.

Absence of a governed assessment remains `NOT_ASSESSED`; it must not be auto-filled to improve portfolio metrics.

## Guardrails frozen by this gate

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

## Acceptance criteria — final result

1. Existing legacy coverage tests remain valid — **PASS**.
2. Product reports explicitly identify the legacy metric semantics — **PASS**.
3. Product reports expose a separate governed-readiness state — **PASS**.
4. Missing governed readiness yields `NOT_ASSESSED`, never `READY` — **PASS**.
5. Portfolio reports aggregate governed readiness separately — **PASS**.
6. Portfolio recommendations no longer imply governed/product publication readiness from legacy coverage alone — **PASS**.
7. Governed-readiness summary status is derived from evidence-backed independent dimensions — **PASS**.
8. Invalid/inconsistent assessments fail closed — **PASS**.
9. At least one real product assessment is materialized conservatively from repository evidence — **PASS (Star Comprehensive)**.
10. Real product/portfolio regeneration proves legacy coverage and governed readiness can diverge safely — **PASS**.
11. Relevant regressions remain green — **PASS: 139 + 14; regressions 0**.

## Closure decision

**CERTIFIED AND FROZEN.**

This gate is complete. Activ One remains `NOT_ASSESSED`; materializing its readiness assessment is explicitly **not** required for this gate and must only happen when its governed evidence is intentionally reviewed. Further tuning of these reporting semantics for metric improvement is out of scope unless future product pressure demonstrates a real contract defect.
