# PHASE-2B — Bajaj Review-Scaling Replication Gate

**Status:** ACTIVE  
**Date:** 2026-08-15

## Purpose

Replicate the certified Phase-2A data-only onboarding and review-risk workflow on a second real commercial Health product: Bajaj General Insurance — My Health Care Plan (Plan 1).

This milestone does not reopen Phase-2A. Phase-2A proved a credible scaling path on Star Comprehensive and is frozen. Phase-2B asks whether the same generic path and review-effort behavior generalize to another insurer/product without product-specific production code.

## Standing acceptance criterion

```text
normal new Health product onboarding
=
0 product-identity-bearing production code
```

No Bajaj-specific reasoning module, branch, parser, routing rule, or publication shortcut is permitted.

## Governed source anchor

Use the already-reviewed current Bajaj My Health Care policy wording version from HEALTH-EXPANSION-1:

- Entity: `bajaj_allianz_general:my_health_care`
- Product: My Health Care Plan (Plan 1)
- Current observed immutable source SHA-256: `05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158`
- UIN: `BAJHLIP26074V022526`
- Registration path: `knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/generic_source_registration/policy_wording_registration_05dc29132434.json`
- Currentness status already established upstream: `current_observed_reviewed`

Currentness evidence is not repeated or weakened in this gate.

## Required generic workflow

Execute the same generic chain proven on Star:

```text
governed registered source
-> governed registered PDF parse
-> currency/sum-insured candidates
-> reviewer-ready currency groups
-> MO-029 review-risk routing
-> Health onboarding batch audit / workload comparison
```

## Measurements

Capture at minimum:

- parsed page count and text-page count;
- extracted currency candidate count;
- reviewer-ready group count;
- candidate-to-group compression ratio;
- Critical / High / Medium / Low routing counts;
- senior-review fraction (`critical + high`) / groups;
- standard/light fraction;
- unresolved-scope / table-binding / unresolved-role flag counts;
- product-identity-bearing production-code changes;
- any real generic capability defect exposed by Bajaj.

## Decision rules

1. Do not tune MO-029 thresholds to improve workload metrics.
2. Do not add product-specific scope cues or branches.
3. A generic upstream improvement is allowed only if the Bajaj evidence demonstrates a reusable deficiency in the existing generic representation.
4. Table, schedule, band or option binding remains fail-closed when the bounded evidence cannot prove the relationship.
5. Reviewer-ready evidence is not a canonical fact and does not authorize publication.
6. A different workload profile from Star is valid evidence; the milestone must report it rather than force convergence.

## Exit criteria

Phase-2B closes when:

```text
Bajaj current governed source parsed through generic ingress
+ real currency candidate workload generated
+ reviewer-ready groups generated
+ MO-029 routing generated
+ workload compared against Star Phase-2A baseline
+ any remaining ambiguity explicitly classified
+ product-identity-bearing production-code changes = 0
+ relevant regressions = 0
```

## Star comparison baseline

The frozen Star Phase-2A baseline is:

- candidates: 12
- reviewer groups: 12
- grouping compression: 0%
- final Critical: 0
- final High: 6
- final Medium: 6
- final Low: 0
- senior-review fraction: 50%
- product-specific production-code changes: 0

This is a comparison baseline only. Bajaj is not required to match it.

## Non-goals

- no frontend;
- no recommendation productization;
- no Motor or Life work;
- no database migration;
- no Bajaj-specific production reasoning;
- no reopening of certified Phase-2A architecture decisions.
