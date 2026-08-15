# HEALTH-EXPANSION-2 — Aditya Birla Activ One NXT Source Governance Gate

**Status:** SELECTED — SOURCE REGISTRATION AUDIT PENDING  
**Date:** 2026-08-15

## Why this is the next Health scaling target

HEALTH-EXPANSION-1 certified that a changed official policy wording can be onboarded as a new immutable version, reviewed for currentness, and passed through the existing publication-eligibility gate without product-specific runtime logic.

The next scaling case should pressure a different failure mode rather than repeat the Bajaj currentness exercise.

Aditya Birla Health Activ One NXT is selected because the repository already contains a published, approved `Super Reload` benefit implementation with explicit policy-wording and prospectus evidence references, including:

- product variant id `pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324`;
- policy wording source id `aditya_birla_health_activ_one_policy_wording_adihlip24097v012324`;
- policy wording SHA-256 `d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451`;
- prospectus source id `aditya_birla_health_activ_one_prospectus_adihlip24097v012324`;
- prospectus SHA-256 `8923d6457d368c9d80d097032a7b784c65b30ba07ae68ea7474af7569332fa56`;
- behavior signature `bsig:activ_one_nxt:super_reload:100pct_unlimited_exhausted_or_insufficient_same_claim`.

The implementation is already richer than a scalar benefit flag. It models trigger requirement, trigger timing, same-hospitalization use, subsequent-hospitalization use, first-claim use, partial restoration use, maximum liability per claim, covered-section scope, utilization sequence, policy-year reset, and floater operation.

## Milestone question

Can the already-published Activ One NXT Super Reload implementation be traced end-to-end to governed immutable source registrations, reviewed document identity/currentness, and the same source hashes it claims — without introducing a product-specific production bypass?

## Immediate audit

First determine whether the exact source hashes referenced by the published benefit implementation are present in the governed source registry or only embedded as evidence references in `insurance_intelligence/benefits/activ_one_nxt.py`.

The milestone must fail closed if:

- a claimed evidence hash has no governed immutable registration;
- a registered source hash differs from the implementation evidence reference;
- product/document identity is unresolved;
- currentness is unresolved where publication requires it;
- prospectus and policy wording are silently treated as equal authority;
- benefit mechanics cannot be traced back to the cited source version.

## Guardrails

- Do not rewrite the Super Reload mechanic model merely to satisfy registration plumbing.
- Do not treat marketing label `Super Reload` as a new generic restoration concept.
- Do not infer currentness from UIN or a working URL alone.
- Do not add Aditya-Birla-specific runtime reasoning.
- Preserve policy wording as primary legal authority and prospectus as corroborating evidence according to existing source-role contracts.
- If the old evidence hashes are no longer current at the official source, onboard new immutable versions rather than mutating old evidence references silently.

## Exit criterion

```text
exact evidence hashes audited
+ immutable governed source registration exists or is created for each required source
+ classification/identity/currentness are reviewed at the correct authority level
+ published Super Reload mechanics remain traceable to governed evidence
+ hash or version drift fails closed
+ no product-specific runtime branch
+ relevant regressions = 0
```
