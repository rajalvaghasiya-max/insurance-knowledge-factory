# HEALTH-EXPANSION-2 — Aditya Birla Activ One NXT Source Governance Gate

**Status:** SUPERSEDED AS PRIMARY MILESTONE — RETAINED AS AUDIT FIXTURE  
**Date:** 2026-08-15

## Governance correction

This file originally selected Aditya Birla Health Activ One NXT as the next Health scaling milestone because the repository already contains a published `Super Reload` implementation with explicit evidence hashes and mechanic-level semantics.

That selection is retained for historical traceability, but it is no longer the primary Phase-2 execution milestone.

The Phase-2 roadmap acceptance criterion is stricter: normal product expansion must happen as governed data, with zero product-identity-bearing production code. Repeating or extending `insurance_intelligence/benefits/activ_one_nxt.py` as the onboarding pattern would normalize plan-specific coding and would be the wrong scaling direction.

## Permitted use of Activ One NXT

Activ One NXT may still be used as an **audit fixture** to answer questions about existing historical product-specific code, including:

- whether its evidence hashes are traceable to governed immutable sources;
- whether old published mechanics remain consistent with current generic contracts;
- whether the historical implementation exposes migration or succession debt;
- whether a future data-only representation can reproduce the same semantics without product-specific runtime code.

It must **not** be used as precedent for creating more product-specific Python modules.

## Hard guardrail

For normal new Health product onboarding:

```text
new product source + governed data/spec artifacts
        ↓
generic registration / classification / identity / currentness
        ↓
generic semantic extraction / review / residue / publication
        ↓
product-identity-bearing production Python changes = 0
```

If a new product cannot be represented safely without production-code changes, that is treated as evidence of a missing reusable semantic capability. Any resulting code change must be generic and product-neutral; insurer/product identity must remain in governed data.

## Relationship to Phase-2A

The active successor milestone is:

`PHASE_2A_DATA_ONLY_HEALTH_ONBOARDING_AND_REVIEW_SCALING_GATE.md`

Activ One NXT can be sampled inside that milestone only as a compatibility/audit fixture. It is not the next plan-specific implementation task.

## Historical evidence references retained

The existing historical implementation references:

- product variant id `pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324`;
- policy wording SHA-256 `d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451`;
- prospectus SHA-256 `8923d6457d368c9d80d097032a7b784c65b30ba07ae68ea7474af7569332fa56`;
- behavior signature `bsig:activ_one_nxt:super_reload:100pct_unlimited_exhausted_or_insufficient_same_claim`.

These references remain useful for succession and traceability review, but no new plan-specific implementation work is authorized by this document.
