# HEALTH-EXPANSION-1 — Bajaj My Health Care Currentness Gate

**Status:** ACTIVE — FRESH BYTE VERIFICATION PENDING  
**Date:** 2026-08-15

## Why this is the next milestone

AR-2.5, AR-3.0 and AFR-N1 are closed. The roadmap therefore returns to Health expansion as governed data rather than new architecture.

Bajaj General Insurance My Health Care Plan is selected as the next product because:

- the product identity is already resolved;
- the registered policy wording is already bound to UIN `BAJHLIP26074V022526`;
- the existing identity overlay deliberately leaves temporal status at `compatibility_unverified`;
- publication eligibility correctly blocks materialized facts while currentness is unresolved;
- the official Bajaj product page currently exposes My Health Care Plan and links its policy wording;
- the linked policy wording currently displays UIN `BAJHLIP26074V022526` and title `MY HEALTH CARE PLAN (PLAN 1)`;
- a retained June 2026 source-observation spec recorded the same official PDF URL with SHA-256 `9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade`, matching the registered document source identity.

This is therefore a currentness-governance completion task, not a new product-specific reasoning task.

## Existing safe behavior

The current fact-publication eligibility contract already blocks `compatibility_unverified` documents.

The gate must not be weakened. The task is to produce stronger currentness evidence for the exact immutable registered document version.

## Required evidence chain

```text
official Bajaj product page
        ↓ links
official My Health Care Plan policy wording URL
        ↓ fresh retrieval
byte comparison against registered immutable document
        ↓
retained official source observation
        ↓
DocumentCurrentnessEvidenceRecord
        ↓ human-reviewed temporal decision
identity overlay temporal_status = current_observed_reviewed
        ↓
existing FactPublicationEligibilityContract
        ↓
eligible_for_publication_review (where all other gates pass)
```

## Current evidence

Registered / prior observed immutable PDF SHA-256:

`9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade`

Official document URL:

`https://www.bajajgeneralinsurance.com/download-documents/health-insurance/Health-PW/My-Health-Care-Plan1-PW.pdf`

Official product page:

`https://www.bajajgeneralinsurance.com/health-insurance-plans/my-health-care-plan.html`

The live official page and linked PDF were externally verified on 2026-08-15, but this verification is not yet promoted into governed currentness because the repository requires a fresh retained byte-identical observation.

## Immediate next action

Perform a fresh governed retrieval of the official PDF and compute SHA-256.

Expected comparison target:

```text
9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade
```

If the fresh official PDF is byte-identical:

1. retain the fresh source observation and official page artifact;
2. build the existing `DocumentCurrentnessEvidenceRecord`;
3. review the evidence and update temporal status through the existing identity-resolution governance path;
4. run publication-eligibility tests without bypassing any gate.

If the hash differs:

1. do not mark the registered document current;
2. register the newly observed document as a new immutable version;
3. review version/identity/currentness before any fact promotion.

## Guardrails

- No fact is published by this milestone.
- A matching UIN alone is insufficient to prove byte identity.
- A working official URL alone is insufficient to prove currentness.
- Marketing-page facts do not replace policy wording.
- No Bajaj-specific reasoning branch is authorized.
- Existing fail-closed publication behavior remains unchanged.

## Exit criterion

```text
fresh official byte comparison retained
+ currentness evidence contract valid
+ temporal decision reviewed
+ publication eligibility behaves through existing generic gate
+ regressions = 0
```
