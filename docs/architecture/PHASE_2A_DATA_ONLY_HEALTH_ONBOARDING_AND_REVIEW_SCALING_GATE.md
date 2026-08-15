# PHASE-2A — Data-Only Health Onboarding & Review-Scaling Gate

**Status:** CERTIFIED  
**Date:** 2026-08-15
**Closure:** `docs/architecture/PHASE_2A_DATA_ONLY_HEALTH_ONBOARDING_AND_REVIEW_SCALING_GATE_CLOSURE.md`

## Purpose

Phase 2 expands PolicyScna across Health products and insurers without returning to plan-specific production coding.

The standing acceptance criterion is:

```text
normal new Health product onboarding
=
0 product-identity-bearing production code
```

Product identity, source lineage, wording version, evidence, facts, rules, mechanics, residue and publication state belong in governed data/spec artifacts. Production code may change only when a genuinely new case proves that the generic semantic model cannot safely represent the required insurance meaning. Such code changes must be reusable and product-neutral.

## Why this gate follows HEALTH-EXPANSION-1

HEALTH-EXPANSION-1 certified Bajaj My Health Care through generic source registration, classification, identity, currentness and publication eligibility without Bajaj-specific runtime logic. It also exposed operational friction: several manual steps were needed to take one product version through the governed path.

The next challenge is therefore not another plan-specific implementation. It is proving that onboarding can scale across multiple products and insurers while code changes and human review effort remain bounded.

## Phase-2A workstreams

### A. Onboarding-path audit

Inventory every step needed to onboard a normal Health product and classify each step as:

- automated generic code;
- governed data/spec input;
- human review;
- product-specific production code;
- manual operational workaround.

Any normal onboarding step that requires product-specific production Python is a scaling defect unless a new generic semantic capability is genuinely required.

### B. MO-029 risk-tiered review operationalization

Review effort must not grow linearly with product count. Operationalize the existing risk-tiered review direction so low-risk deterministic cases can pass through lighter review while high-risk semantic or publication-sensitive cases receive deeper review.

The goal is not to remove human review. The goal is to concentrate it where uncertainty and customer impact justify it.

### C. Diverse Health batch

Select a small, deliberately diverse batch of Health products across multiple insurers and onboard them through the generic path as governed data only.

The batch should vary in benefit mechanics, waiting periods, limits, restoration/reload behavior, optional covers and document structures so it can expose real representational gaps.

No plan receives a dedicated production reasoning module merely because its marketing labels or mechanics differ.

### D. Scaling measurements

For each product record at minimum:

- production-code files changed;
- product-identity-bearing production-code changes;
- governed spec/data artifacts added;
- source documents registered;
- evidence candidates generated;
- human-review decisions required;
- material residue count;
- unsupported semantic cases;
- onboarding defects/fail-closed events;
- elapsed manual review effort where measurable.

## Hard acceptance rules

1. **Zero product-identity-bearing production code for normal onboarding.**
2. Product-specific facts/mechanics live in governed data, not `if product == ...` branches.
3. A new Python abstraction is allowed only when product pressure proves the existing generic model cannot safely represent the fact.
4. Any new abstraction must be generic, reusable and product-neutral.
5. Source/version/currentness failures remain fail closed.
6. Unknown or unresolved semantics become explicit residue; they are not flattened or guessed.
7. Published/readiness state is separate from semantic representation.
8. No frontend, recommendation-productization, Motor or Life scope is introduced here.
9. Database migration remains trigger-driven; Phase 2A does not create a storage migration by default.

## Historical product-specific implementations

Existing files such as `insurance_intelligence/benefits/activ_one_nxt.py` may be retained as historical compatibility/audit fixtures where they still serve validated behavior or succession evidence.

They are **not** the scaling template for new products.

Phase 2A should eventually determine whether such historical product-specific implementations can be represented by generic governed data and then safely fenced, migrated or retired under normal succession rules.

## Exit criteria

Phase 2A is certified only when:

```text
onboarding workflow mapped
+ MO-029 review tiers operationalized
+ diverse Health batch onboarded across multiple insurers
+ normal-product production-code changes = 0
+ product-identity-bearing production-code changes = 0
+ material residue explicit
+ review effort measured and showing a credible path to sub-linear scaling
+ relevant subsystem regressions = 0
```

## Certification result

All exit criteria are satisfied as documented in the closure record.

The critical review-scaling evidence is a real Star Comprehensive reviewer workload in which generic, evidence-bounded scope improvements reduced senior-review demand from 12/12 groups to 6/12 groups while preserving MO-029 thresholds and fail-closed behavior. This establishes a credible scaling path without claiming that cross-product sub-linear scaling has already been empirically proven.

## Next-phase boundary

Do not reopen Phase-2A to pursue further Star-specific optimization merely to improve the metric. Remaining high-risk Star groups are explicit structural residue involving table/column binding, unresolved monetary role, or missing section context.

Continue Phase 2 under the roadmap with normal Health expansion as governed data only. Any future real-product pressure that exposes a generic representational gap may justify a reusable product-neutral capability; otherwise the standing acceptance criterion remains zero product-identity-bearing production code.
