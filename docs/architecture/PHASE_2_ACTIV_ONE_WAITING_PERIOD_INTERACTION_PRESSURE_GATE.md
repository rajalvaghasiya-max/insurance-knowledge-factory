# Phase 2 — Activ One Waiting-Period Interaction Pressure Gate

**Status:** ACTIVE — CURRENT GOVERNED SEMANTIC PRESSURE STARTED  
**Date:** 2026-08-15

## Purpose

Exercise the current governed Aditya Birla Activ One policy wording against the existing generic Health waiting-period extraction and semantic contracts, with particular pressure on interactions between base waiting periods, optional reductions, schedule-selected alternatives, and benefit-specific waivers.

This is not a new waiting-period subsystem and is not a legacy Activ One/NXT migration exercise.

## Governed source under pressure

- Insurer: Aditya Birla Health Insurance
- Product: Activ One
- Entity: `aditya_birla_health:activ_one`
- UIN: `ADIHLIP24097V012324`
- Current governed policy-wording SHA-256: `38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16`
- Archive path: `archive/raw_pdf/aditya_birla_health/policy_wording/activ_one_current_20260815.pdf`
- Canonical parsed artifact: `processed/pdf_parse/38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16.json`

The historical missing Activ One policy wording SHA `d772...` and the historical Activ One NXT intelligence artifacts are not authority for this gate and must not be imported as current truth.

## Why this pressure case

The three-product review-scaling replication checkpoint closed the cross-insurer empirical review-routing gap. The next useful Health pressure should therefore exercise a materially different semantic interaction rather than repeat currency extraction.

The current Health intelligence coverage review still identifies Activ One waiting periods as not automated, while the current governed wording contains multiple interacting waiting-period structures. Existing generic waiting-period contracts already model base waits, reductions, waivers, schedule/table delegation, continuity, and selected alternatives, so the correct test is whether current Activ One can be represented by those contracts without product-specific runtime logic.

## Existing generic path

The starting evidence path is:

`current governed parsed wording -> waiting-period duration candidates -> evidence consolidation -> human semantic review against existing waiting-period contracts`

Existing primitives:

- `WaitingPeriodDurationParser`
- `WaitingPeriodCandidateConsolidator`
- `insurance_intelligence.concepts.waiting_periods.policy`

The extraction/consolidation stages are evidence-only and do not establish applicability or publication.

## Standing acceptance criterion

```text
current Activ One waiting-period pressure
=
0 product-identity-bearing production code
```

A new generic abstraction is allowed only if the current governed wording proves that the existing waiting-period contract cannot safely represent a real semantic interaction.

## Semantic pressure expected from the current wording

The gate will examine, without assuming publication:

1. base Pre-Existing Disease waiting period;
2. base specified-disease/procedure waiting period;
3. base initial waiting period;
4. optional reduction of specified-disease waiting period;
5. optional reduction of PED waiting period with schedule-selected alternatives;
6. benefit-specific waiting-period waivers/exceptions for chronic-care coverage;
7. any Critical Illness or other benefit-scoped waiting period that must not be flattened into a product-wide base wait;
8. schedule/table-dependent applicability and unresolved residue.

## Guardrails

- Use only the current governed `38bb...` wording for current semantic evidence.
- Do not copy values from historical Activ One NXT intelligence as facts.
- Do not flatten optional reductions, waivers, or benefit-scoped waits into one scalar product waiting period.
- Do not infer a schedule-selected option unless the governed evidence binds it.
- Preserve benefit scope and interaction semantics explicitly.
- Unknown schedule/table binding remains unresolved and fail-closed.
- No automatic adjudication or publication.
- No insurer/product-specific production branch, source-hash branch, or threshold change.
- No frontend, Motor, Life, database migration, recommendation-productization, or public-launch scope.

## Measurements

Record at minimum:

- duration candidates and pages;
- consolidated groups by waiting-period category/duration;
- repeated/multiple-duration flags;
- schedule/option-layout flags;
- benefit/service-scope flags;
- semantic interactions representable by the existing waiting-period contracts;
- unresolved residue requiring schedule/table or benefit-scope binding;
- product-identity-bearing production-code changes;
- adjudication/publication side effects.

## Exit condition

This gate closes when the current governed Activ One wording has exercised the generic waiting-period evidence path, the resulting base/optional/waiver interactions have been mapped against the existing generic waiting-period contracts without importing legacy truth, any genuinely reusable representational defect has been handled generically, relevant regressions are green, and unresolved schedule/table applicability remains explicit rather than guessed.
