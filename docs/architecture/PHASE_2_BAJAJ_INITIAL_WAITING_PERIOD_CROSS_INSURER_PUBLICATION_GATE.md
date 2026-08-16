# Phase 2 — Bajaj Initial Waiting-Period Cross-Insurer Publication Gate

**Status:** ACTIVE — STALE-ANCHOR SAFEGUARD IMPLEMENTED; CURRENT-SOURCE REVERIFICATION PENDING  
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

## Generic stale-anchor safeguard

Independent review identified a manufacturing-scale weakness: the correct historical/current SHA mismatch was noticed manually, but repeated manufacturing needs the mismatch to fail closed mechanically.

Implemented generic contract:

```text
factory_core/governance/source_reverification.py
```

The contract contains no insurer/product-specific decision logic. It compares a reviewed semantic artifact's immutable source SHA with the current governed source SHA.

```text
same SHA
  -> CURRENT_ANCHOR_MATCH
  -> CONTINUE

different SHA
  -> REVERIFICATION_REQUIRED
  -> WITHHELD
  -> reason = source_reverification_required
```

A stale reviewed proposition can be rechecked against the current source with exactly four outcomes:

```text
CONFIRMED
DIFFERS
NOT_PRESENT
AMBIGUOUS
```

Only `CONFIRMED` permits the prior semantic proposition to continue unchanged. The other outcomes remain positively withheld:

```text
DIFFERS     -> current_source_differs_semantic_review_required
NOT_PRESENT -> current_source_proposition_not_present
AMBIGUOUS   -> current_source_reverification_ambiguous
```

This keeps reverification from becoming a confirmation ritual. A changed current rule is new semantic-review work, not a successful confirmation of historical truth.

The real Bajaj SHA transition is used only as a test pressure case:

```text
9479... -> 05dc... -> REVERIFICATION_REQUIRED / WITHHELD
```

Production logic remains insurer-independent.

## Gate sequence

1. Locate/parse the current `05dc...` policy wording through the existing governed source path.
2. Apply the generic source-anchor contract to the historical reviewed mapping.
3. Reverify the initial-wait duration, subject, start basis, scope, and accident exception from current-source evidence.
4. Record one of `CONFIRMED / DIFFERS / NOT_PRESENT / AMBIGUOUS` with a concrete current evidence reference.
5. Only if current evidence confirms the bounded proposition, materialize one governed rule-certification case as data using the existing insurer-independent case loader and `waiting_period` topic definition.
6. Run the existing generic RuleCertificationRunner.
7. Pressure the existing publication-decision and authoritative-publication gates.
8. Keep any unrelated Bajaj waiting-period residue unresolved; publishing one bounded rule must not imply product-wide waiting-period completeness.
9. Run focused and broader regressions.

## Acceptance criteria

- current immutable source SHA `05dc...` is the authoritative evidence source;
- historical `9479...` artifacts are used only as prior/historical locators, never current proof;
- stale source anchors are mechanically classified `REVERIFICATION_REQUIRED` and positively withheld;
- reverification has explicit fail-closed outcomes and a concrete evidence reference;
- the bounded initial-wait rule is fully represented with no semantic loss if current evidence confirms it;
- accident exception is preserved explicitly if present in current evidence;
- no Bajaj-specific production reasoning code is added;
- no new ontology abstraction unless current-source pressure proves a real generic gap;
- certification/publication is scoped to this rule only;
- unresolved PED/specific-disease/schedule-bound residue remains unresolved;
- no whole-product readiness or publication claim is inferred;
- relevant regressions remain green.

## Current conclusion

The candidate remains architecturally suitable. The stale-anchor safeguard is now implemented generically; publication work remains blocked until the current `05dc...` source itself establishes the rule outcome. That blocker is explicit, auditable, and resumable rather than an implicit absence.
