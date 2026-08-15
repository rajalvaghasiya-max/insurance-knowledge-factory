# Phase-2C — Activ One Third-Insurer Review-Scaling Gate

Status: **ACTIVE — THIRD-INSURER REPLICATION STARTED**
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

The same generic path used for Star Comprehensive and Bajaj My Health Care is the starting point:

`governed current source -> canonical PDF parse -> currency candidates -> reviewer-ready groups -> MO-029 risk routing`

No Activ One-specific reasoning module, product branch, source-hash branch or threshold change is allowed.

## Why Activ One is the next pressure case

Phase-2A demonstrated the review-scaling mechanism on Star Comprehensive. Phase-2B replicated it on Bajaj My Health Care and exposed a reusable role-hint precision defect that was fixed generically without weakening genuine risk.

Activ One now provides a third insurer and a different document/product structure while reusing a source whose current version and authority have already been governed. This makes it a clean test of cross-insurer pipeline repeatability rather than another currentness exercise.

## Measurements

Record at minimum:

- parsed pages and text-bearing pages;
- currency candidates;
- reviewer-ready groups;
- grouping compression;
- MO-029 Critical / High / Medium / Low counts;
- flags driving Critical/High routes;
- unsupported or unresolved semantic residue;
- product-identity-bearing production-code changes;
- adjudication/publication side effects, which must remain none.

## Guardrails

- Historical missing Activ One policy wording SHA `d772...` must never be reconstructed or equated to the current `38bb...` version.
- Historical retained prospectus evidence must not substitute for the current policy wording.
- Existing `insurance_intelligence/benefits/activ_one_nxt.py` remains a historical compatibility/audit fixture and is not the scaling pattern.
- Source observation/currentness evidence does not itself publish facts.
- Unknown table, band, role or section bindings stay explicit and fail closed.
- No MO-029 threshold weakening to improve workload metrics.
- No frontend, Motor, Life, database migration or recommendation-productization scope.

## Exit condition

Phase-2C closes only when the current Activ One wording has run through the same generic reviewer-workload path, any demonstrated reusable defect is handled generically, relevant regressions are green, and normal-product pressure remains at zero product-identity-bearing production code.
