# Phase-2B — Bajaj My Health Care Review-Scaling Replication Checkpoint

Status: **CERTIFIED — CROSS-PRODUCT REPLICATION COMPLETE AND REGRESSION-CLEAN**
Date: 2026-08-15

## Purpose

Replicate the Phase-2A governed review-scaling path on a second real Health product and insurer without product-identity-bearing production code.

Product under pressure:

- Insurer: Bajaj General Insurance
- Product: My Health Care Plan (Plan 1)
- Entity: `bajaj_allianz_general:my_health_care`
- Registered source SHA-256: `05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158`

## Generic pipeline execution

The existing generic path was executed without new product-specific production code:

`governed registration -> governed registered PDF parse -> currency candidates -> reviewer-ready groups -> MO-029 review-risk routing`

Observed Bajaj workload:

- Parsed pages: **53**
- Pages with text: **53**
- Currency candidates: **10**
- Reviewer-ready groups: **10**
- Grouping compression: **0%**
- Adjudication created: **none**
- Publication created: **none**
- Product-identity-bearing production code added for this replication: **0**

## Initial routing result

Initial MO-029 distribution:

- Critical: **2**
- High: **5**
- Medium: **3**
- Low: **0**

Inspection showed both Critical groups were Family Visit benefit limits. The bounded evidence contained explicit phrases such as `Upto INR 25,000` and `Upto INR 50,000`, but the extraction primitive's nearest-role-cue rule selected a later nearby `premium` token from `Renewal premium waiver`, creating `possible_benefit_limit_despite_role_hint` and therefore a Critical route.

This was a generic role-hint precision defect, not a Bajaj-specific semantic rule.

## Evidence-backed generic correction

The generic currency parser was changed so an immediate pre-amount limit phrase such as `up to` / `upto` receives precedence as `sub_limit_or_limit` before the more distant nearest-cue fallback is used.

Guardrails preserved:

- no Bajaj product ID, source hash, product branch, or product-specific reasoning was introduced;
- normal premium clauses still retain the `premium` role;
- sum-insured-band binding remains unresolved;
- MO-029 thresholds were not changed;
- no fact acceptance, adjudication, or publication was added.

Focused regression after the correction: **14 passed**.

## Measured post-fix result

The same Bajaj parsed artifact was rerun through candidate extraction, reviewer grouping, and MO-029 routing.

Post-fix distribution:

- Critical: **0**
- High: **7**
- Medium: **3**
- Low: **0**

Therefore:

- false Critical escalations changed from **2 -> 0**;
- the two Family Visit groups correctly remain High because `schedule_or_band_binding_unverified` is still material;
- total Critical/High workload remains **7 / 10 (70%)**;
- review-tier precision improved without reducing genuine senior-review demand.

This distinction is important: the objective was not to make the metric look better. The correction removed an incorrect severity reason while preserving legitimate band-binding uncertainty.

## Cross-product comparison with Star Comprehensive

Comparable real currency-review workloads now show:

### Star Comprehensive

- Reviewer-ready groups: **12**
- Critical: **0**
- High: **6**
- Medium: **6**
- Critical/High: **6 / 12 (50%)**

### Bajaj My Health Care

- Reviewer-ready groups: **10**
- Critical: **0**
- High: **7**
- Medium: **3**
- Critical/High: **7 / 10 (70%)**

The same generic pipeline therefore works across two insurers/products while correctly preserving different review-cost distributions.

## Regression closure

Relevant subsystem regressions after the generic parser correction are green:

- Health: **116 passed**
- factory_core: **127 passed**
- focused role/scope/routing set: **14 passed**

No regression was observed in the relevant Health or governance-core surfaces.

## Certification decision

**Phase-2B is CERTIFIED.**

The certification claim is deliberately narrow:

1. the generic governed review path replicated on a second real insurer/product with zero product-identity-bearing production code;
2. cross-product pressure exposed one reusable extraction precision defect, which was corrected generically;
3. false Critical escalation was eliminated without weakening MO-029 or suppressing genuine High-risk sum-insured-band ambiguity;
4. the correction is regression-clean across the relevant Health and factory-core test suites;
5. no adjudication, canonical fact selection, publication, or product-specific reasoning was introduced.

This certification does **not** claim that dense table/band structures are solved automatically. The remaining seven High groups are legitimate unresolved review work and remain fail-closed.

## Freeze rule

Phase-2B is frozen after certification. Do not continue tuning Bajaj solely to reduce High counts. Reopen only for a real regression or if later product pressure independently proves a reusable generic table/band recovery requirement.

## Guardrails

- No publication or adjudication follows from review routing.
- No product-specific production reasoning code.
- No weakening of fail-closed review-risk policy.
- Table/column and sum-insured-band ambiguity remain unresolved until evidence supports binding.
- Cross-product review effort is measured honestly; unfavorable workload distributions are not normalized away.
