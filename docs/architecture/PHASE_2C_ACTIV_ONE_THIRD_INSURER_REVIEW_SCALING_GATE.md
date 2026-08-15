# Phase-2C — Activ One Third-Insurer Review-Scaling Gate

Status: **CERTIFIED — THIRD-INSURER REPLICATION COMPLETE AND FROZEN**
Date: 2026-08-15

## Purpose

Replicate the certified data-only reviewer-workload path on a third real Health insurer/product using the current governed Activ One policy wording.

Product under pressure:

- Insurer: Aditya Birla Health Insurance
- Product: Activ One
- Entity: `aditya_birla_health:activ_one`
- Current governed policy-wording SHA-256: `38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16`
- Current archive path: `archive/raw_pdf/aditya_birla_health/policy_wording/activ_one_current_20260815.pdf`
- Currentness status already reviewed separately; this gate does not re-decide currentness or publication.

## Standing acceptance criterion

```text
normal new Health product pressure
=
0 product-identity-bearing production code
```

The same generic path used for Star Comprehensive and Bajaj My Health Care was executed:

`governed current source -> canonical PDF parse -> currency candidates -> reviewer-ready groups -> MO-029 risk routing`

No Activ One-specific reasoning module, product branch, source-hash branch or threshold change was introduced.

## Generic source-contract pressure

Activ One exposed a governed-source shape not previously exercised by this parser bridge: a reviewer-supplied registered PDF whose provenance is anchored by the registration's archive locator and immutable SHA-256, with no source URL by design.

Two generic contract corrections were required:

1. governed registered PDF parsing now permits `source_url = null` while still requiring the registered archive path to remain under `archive/` and the bytes to match the registered SHA-256;
2. the shared Health extraction-candidate contract permits a null source URL only when `provenance_status = governed_source_registration_sha256_verified`.

Ordinary/non-governed candidate sources still require a non-empty URL. These changes do not infer identity/currentness or create facts/publication state.

Focused regression for the URL-less governed path: **8 passed**.

## Measured Activ One workload

- Parsed pages: **56**
- Pages with text: **56**
- Currency candidates: **11**
- Reviewer-ready groups: **11**
- Grouping compression: **0%**
- MO-029 Critical: **0**
- MO-029 High: **11**
- MO-029 Medium: **0**
- MO-029 Low: **0**
- Critical/High groups: **11 / 11 (100%)**
- Adjudication created: **none**
- Publication created: **none**
- Product-identity-bearing production code added: **0**

## High-risk diagnostic

The eleven High groups are not one repeated defect.

Observed evidence includes:

- dense Product Benefit Table values on page 47 where flattened text does not safely preserve column/row binding;
- monetary role ambiguity for option values such as INR 15,000 / INR 25,000 and Critical Illness / Personal Accident SI options;
- explicit sum-insured ranges on page 31 whose surrounding medical-test table requires structural binding;
- Advanced Health Check-up and other sub-limits that remain subject to schedule/SI binding;
- a page-40 INR 50,000 travel-fare clause whose human-readable benefit heading sits outside the bounded candidate window.

The dominant flags are legitimate combinations of `benefit_scope_unresolved`, `schedule_or_band_binding_unverified`, `sum_insured_band_scope_unresolved`, and for some groups `unresolved_role_hint`.

## Bounded scope-cue experiment

Real Activ One pressure justified adding two reusable review-only scope labels:

- `compassionate_visit`
- `advanced_health_checkup`

Focused scope/routing regressions after these additions: **18 passed**.

However, rerunning the real Activ One workload produced the same distribution: **0 Critical / 11 High / 0 Medium / 0 Low**. The labels were therefore valid but did not reduce this workload. In particular, the Compassionate Visit heading is outside the bounded evidence window for the page-40 amount.

This no-effect result is retained honestly. The implementation is not extended to infer Compassionate Visit from body wording such as two-way travel fare merely to reduce review counts, because that would cross from explicit bounded scope cues toward semantic reconstruction.

## Cross-product comparison

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

### Aditya Birla Activ One

- Reviewer-ready groups: **11**
- Critical: **0**
- High: **11**
- Medium: **0**
- Critical/High: **11 / 11 (100%)**

The same generic governed pipeline therefore operates across three insurers/products while preserving materially different review-cost distributions. Activ One demonstrates that cross-product replication does not imply uniform or automatically reduced human-review effort.

## Regression closure

Final relevant regressions:

- Health subsystem: **120 passed**
- `factory_core`: **128 passed**
- Regressions observed: **0**

These closure runs confirm that the URL-less governed-source support, shared extraction-contract correction, and Activ One pressure work introduced no broader regression in the relevant subsystems.

## Certified architecture conclusions

Phase-2C certifies the following narrow claims:

1. third-insurer pipeline repeatability with zero product-identity-bearing production code;
2. support for a second legitimate governed provenance shape — reviewer-supplied, hash-verified registered PDFs without a source URL;
3. honest fail-closed behavior under dense tables and option/band structures;
4. no need to weaken MO-029 or invent product-specific scope logic merely to improve metrics;
5. review-cost distributions are product-structure dependent and must be measured rather than normalized away.

The remaining Activ One High groups remain legitimate unresolved review work. No structural table resolver is introduced by this gate. Such a capability should only be considered if future independent product pressure demonstrates a reusable need.

## Guardrails

- Historical missing Activ One policy wording SHA `d772...` must never be reconstructed or equated to the current `38bb...` version.
- Historical retained prospectus evidence must not substitute for the current policy wording.
- Existing `insurance_intelligence/benefits/activ_one_nxt.py` remains a historical compatibility/audit fixture and is not the scaling pattern.
- Source observation/currentness evidence does not itself publish facts.
- Unknown table, band, role or section bindings stay explicit and fail closed.
- No MO-029 threshold weakening to improve workload metrics.
- No frontend, Motor, Life, database migration or recommendation-productization scope.

## Closure decision

**Phase-2C is CERTIFIED and frozen.**

Do not continue optimizing Activ One under this gate. Reopen only for a demonstrated regression or if future independent product pressure proves a reusable generic capability is required.
