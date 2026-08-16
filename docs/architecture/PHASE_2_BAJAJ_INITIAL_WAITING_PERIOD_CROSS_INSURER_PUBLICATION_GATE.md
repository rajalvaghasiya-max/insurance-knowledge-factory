# Phase 2 — Bajaj Initial Waiting-Period Cross-Insurer Publication Gate

**Status:** CERTIFIED AND FROZEN  
**Date:** 2026-08-16

## Purpose

Prove that one consequential Bajaj My Health Care rule can travel through the existing insurer-independent certification/publication path without Bajaj-specific production reasoning.

This is a scaling-pressure gate, not a new architecture project.

## Selected pressure case

Candidate atomic rule:

```text
bajaj_mhc_initial_base_wait
```

Historical reviewed mapping described:

```text
waiting_period_type = INITIAL
duration            = 30 DAYS
start_basis         = POLICY_INCEPTION / first commencement
subject             = illness treatment
exception           = accident claims
```

The existing generic topic catalogue represents this through `waiting_period` components:

- `waiting_period_duration`
- `waiting_period_subject`
- `start_basis`
- `applicability_scope`
- `continuity_or_credit_rule`
- `exception_condition`

No new semantic abstraction was required.

## Critical provenance boundary

The detailed historical Bajaj waiting-period mapping was anchored to:

```text
9479fe6f6ce729f95f75c43e9ef00c76f4aa8917650783fe8f5d7cb37844cade
```

The certified current Bajaj My Health Care policy wording is:

```text
SHA-256 = 05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
UIN     = BAJHLIP26074V022526
state   = current_observed_reviewed
```

The historical reviewed proposition was therefore not promoted as current truth until independently reverified against the current `05dc...` source.

## Generic stale-anchor safeguard

Independent review identified a manufacturing-scale weakness: the correct historical/current SHA mismatch had been noticed manually, but repeated manufacturing required the mismatch to fail closed mechanically.

Implemented generic contract:

```text
factory_core/governance/source_reverification.py
```

The contract contains no insurer/product-specific decision logic.

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

Only `CONFIRMED` permits the prior semantic proposition to continue unchanged. The other outcomes remain positively withheld.

The real Bajaj transition is covered as the pressure case:

```text
9479... -> 05dc... -> REVERIFICATION_REQUIRED / WITHHELD
```

Production logic remains insurer-independent.

## Current-source reverification result

The current `05dc...` policy wording independently confirms the bounded initial-wait rule on page 21, with the plan value also corroborated on page 53.

Governed outcome:

```text
reverification_outcome = CONFIRMED
```

The bounded current semantics are:

```text
Initial wait       : 30 days
Subject            : expenses related to treatment of any Illness
Start              : first Policy commencement date
Accident exception : accident claims, if otherwise covered
Continuity rule    : exclusion does not apply after >12 months continuous coverage
```

The current-source re-verification is materialized at:

```text
knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/governance/initial_waiting_period_source_reverification.json
```

Historical `9479...` evidence remains historical only and is not used as current proof.

## Generic rule certification

A data-only certification case was materialized at:

```text
knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/generic_rule_certification/initial_waiting_period_certification_case.json
```

The unchanged generic rule-certification loader and runner were used.

Result:

```text
outcome      = PASS
completeness = COMPLETE
explanation  = permitted
```

All six bounded semantic components are satisfied and anchored only to current source SHA `05dc...`.

The certification deliberately preserves the limitation that unrelated Bajaj waiting-period residue remains unresolved.

## Publication decision and authoritative publication

The same certified governed-data case was passed through the existing generic P2.3 publication-decision evaluator and P2.4 authoritative-publication gate.

No Bajaj-specific production publication module was added.

The bounded rule successfully reached authoritative publication while preserving the certification limitations and evidence traces.

This publication applies only to the certified initial waiting-period rule. It does not publish or resolve:

- PED waiting periods;
- specified disease/procedure waiting periods;
- teleconsultation waiting periods;
- investigation-benefit waiting periods;
- schedule-bound waiting-period values;
- whole-product waiting-period completeness;
- whole-product governed readiness.

## What this gate proves

This gate establishes a meaningful second-insurer manufacturing proof:

```text
current governed source
-> stale-anchor detection/reverification
-> governed semantic evidence
-> generic rule certification
-> generic publication decision
-> generic authoritative publication
```

The pipeline handled Bajaj without a new ontology abstraction and without Bajaj-specific production reasoning.

This proves cross-insurer reuse for this semantic shape and governance path. It does not claim that every future insurance semantic pattern is already solved.

## Regression evidence

Focused source-reverification + Bajaj certification/publication suite:

```text
15 passed
```

Broader regressions:

```text
factory_core             : 148 passed
health                   : 124 passed
insurance_intelligence   : 2909 passed
failures                 : 0
```

## Acceptance criteria closure

- current immutable source SHA `05dc...` used as authoritative evidence source — PASS;
- historical `9479...` retained only as historical locator — PASS;
- stale source anchors mechanically fail closed — PASS;
- explicit reverification outcomes available — PASS;
- current proposition independently reverified — PASS (`CONFIRMED`);
- bounded rule represented without semantic loss — PASS;
- accident exception preserved — PASS;
- >12-month continuous-coverage exception preserved — PASS;
- zero Bajaj-specific production reasoning code — PASS;
- no new ontology abstraction — PASS;
- generic certification reused — PASS;
- generic publication decision reused — PASS;
- generic authoritative-publication gate reused — PASS;
- unrelated waiting-period residue remains unresolved — PASS;
- no whole-product readiness/publication inference — PASS;
- regressions green — PASS.

## Final conclusion

**CERTIFIED AND FROZEN.**

The Bajaj initial waiting-period pressure case has demonstrated that PolicyScna can manufacture one bounded, current, governed insurance rule for a second insurer through the existing generic certification and publication architecture without introducing product-specific production reasoning.

No further tuning of this gate is justified. Future work should apply the manufacturing pattern to additional real Health knowledge pressure rather than optimize this completed proof.
