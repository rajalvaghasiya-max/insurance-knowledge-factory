# Phase 2 — Bajaj Initial Waiting-Period Cross-Insurer Publication Gate

**Status:** ACTIVE — CURRENT-SOURCE REVERIFICATION REQUIRED  
**Date:** 2026-08-16

## Purpose

Prove that one consequential Bajaj My Health Care rule can travel through the existing insurer-independent certification/publication path without Bajaj-specific production reasoning.

This is a scaling-pressure gate, not a new architecture project.

## Selected pressure case

Candidate atomic rule:

```text
bajaj_mhc_initial_base_wait
```

Historical reviewed mapping describes:

```text
waiting_period_type = INITIAL
duration            = 30 DAYS
start_basis         = POLICY_INCEPTION / first commencement
subject             = illness treatment
exception           = accident claims
```

The existing generic topic catalogue already represents this through `waiting_period` components:

- `waiting_period_duration`
- `waiting_period_subject`
- `start_basis`
- `applicability_scope`
- optional `exception_condition`

No new semantic abstraction is justified by this candidate.

## Critical provenance boundary

The detailed MO-028B Bajaj waiting-period atomic inventory and reviewed mapping are bound to historical source SHA:

```text
9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade
```

The certified current Bajaj My Health Care policy wording is:

```text
SHA-256 = 05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
UIN     = BAJHLIP26074V022526
state   = current_observed_reviewed
```

Therefore the historical reviewed 30-day rule MUST NOT be promoted as current governed truth until the same proposition is independently reverified against the current `05dc...` bytes.

## Gate sequence

1. Locate/parse the current `05dc...` policy wording through the existing governed source path.
2. Reverify the initial-wait duration, subject, start basis, scope, and accident exception from current-source evidence.
3. If current evidence matches, materialize one governed rule-certification case as data using the existing insurer-independent case loader and `waiting_period` topic definition.
4. Run the existing generic RuleCertificationRunner.
5. Pressure the existing publication-decision and authoritative-publication gates.
6. Keep any unrelated Bajaj waiting-period residue unresolved; publishing one bounded rule must not imply product-wide waiting-period completeness.
7. Run focused and broader regressions.

## Acceptance criteria

- current immutable source SHA `05dc...` is the authoritative evidence source;
- historical `9479...` artifacts are used only as prior/historical locators, never current proof;
- the bounded initial-wait rule is fully represented with no semantic loss;
- accident exception is preserved explicitly;
- no Bajaj-specific production reasoning code is added;
- no new ontology abstraction unless current-source pressure proves a real generic gap;
- certification/publication is scoped to this rule only;
- unresolved PED/specific-disease/schedule-bound residue remains unresolved;
- no whole-product readiness or publication claim is inferred;
- relevant regressions remain green.

## Current conclusion

The candidate is architecturally suitable, but publication work is blocked pending current-source reverification. That blocker is intentional and demonstrates the governance system is preventing historical evidence from silently becoming current truth.
