# Phase 2 — Restoration Stateful-Mechanic Manufacturing Pressure Gate

**Status:** ACTIVE — CURRENT-SOURCE QUALIFICATION COMPLETE; GENERIC EVALUATOR EXECUTION PROOF REQUIRED  
**Date:** 2026-08-16

## Purpose

Test whether PolicyScna can manufacture a current-source restoration/reinstatement rule as governed declarative parameters, execute it through an insurer-independent state evaluator, derive claim-sequence consequences from governed timing semantics, and publish only the resolved bounded mechanics.

This is not a Bajaj restoration subsystem. It is the first deliberate pressure case where the governed rule describes a state function rather than a static assertion.

## Primary pressure case

```text
Bajaj General Insurance — My Health Care
UIN: BAJHLIP26074V022526
current governed source SHA-256:
05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
```

Every Bajaj restoration proposition in this gate is re-derived from current `05dc...`. Historical Star/Activ One restoration implementations may be reused only as representation pressure/context, never as current Bajaj truth.

## Current-source qualification

Operative wording is on page 17 under `15. Sum Insured Reinstatement`.

Resolved asserted semantics:

```text
reinstated SI use              = subsequent claim
minimum subsequent gap         = 15 days from discharge
other-beneficiary gap exception= yes
covered section                = Inpatient Hospitalization Treatment
maximum liability per claim    = Inpatient Hospitalization Sum Insured
carry forward                  = no
floater operation              = policy level
individual operation           = insured-beneficiary level
```

Page 52 independently establishes the recurrence bands:

```text
SI < INR 5 lakh  -> once
SI >= INR 5 lakh -> unlimited
```

The page-52 parenthetical `(Available for same illness)` remains scope-sensitive and is not silently promoted to a clean same-illness Boolean.

Current unresolved semantics include:

- exact activation trigger;
- restored amount/percentage;
- exact scope of same-illness use;
- different-illness rule if not independently established;
- bonus participation;
- any mechanics not explicitly supported by the current source.

Qualification is materialized at:

```text
knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/governance/restoration_stateful_mechanic_current_source_qualification.json
```

## Asserted versus derived state result

The current source explicitly says reinstated SI is available for a **subsequent claim** and normally requires a gap measured from discharge.

Therefore the headline triggering-claim result is derived rather than invented:

```text
triggering_claim_can_consume_reinstatement = false
provenance = DERIVED_FROM_GOVERNED_ASSERTED_SEMANTICS
```

This derivation does not require the unresolved activation trigger to be guessed. A negative triggering-claim usability result follows from the resolved effective-point/claim-sequence constraint.

## Non-optional headline acceptance scenario

```text
Base Sum Insured: INR 10 lakh
Single first hospitalization claim: INR 15 lakh
Prior restorations: 0
Question: can restored SI fund the INR 5 lakh overflow on the triggering claim?
```

Expected bounded state result from current wording:

```text
REINSTATEMENT_NOT_USABLE_FOR_TRIGGERING_CLAIM_OVERFLOW
```

This does not decide overall claim payment or other benefits.

## Existing architecture pressure result

The existing governed restoration concept already distinguishes descriptive dimensions such as trigger requirement/timing, same-hospitalization use, subsequent-hospitalization use, recurrence and other mechanics.

However, no insurer-independent executable restoration state evaluator was found. Existing product implementations describe mechanics but do not execute claim-state transitions.

Current-source pressure therefore justified the smallest generic runtime addition:

```text
insurance_intelligence/benefits/restoration_state.py
```

The evaluator is intentionally bounded to closed declarative semantics for claim sequence, trigger-resolution state, recurrence bands, hospitalization-gap rules, illness-relationship rules and covered-section scope. It does not calculate claim payment or restored amount.

## Data/logic boundary — mechanical falsifier

The evaluator contains no insurer/product identity branch and accepts only a closed vocabulary.

A second materially different non-product conformance rule must execute through the same evaluator unchanged. The current contrast fixture uses:

```text
activation trigger state    = resolved
activation effective point  = within triggering claim
frequency                   = once
same-illness subsequent use = not allowed
different-illness use       = allowed
SI bands                    = none / one universal band
```

This is intentionally different from the current Bajaj shape.

Free-form embedded algorithms such as:

```text
if base_si_exhausted and previous_restorations < ...
```

are rejected by the contract rather than interpreted.

A synthetic contrast pass proves rule-shape portability only. It is not real cross-insurer restoration proof.

## Counterfactual execution currently covered

The focused evaluator test suite requires:

- Bajaj triggering claim -> NOT_ELIGIBLE for reinstatement consumption, derived from `SUBSEQUENT_CLAIM_ONLY`;
- Bajaj subsequent same-illness claim -> remains UNRESOLVED while trigger and parenthetical illness scope are unresolved;
- Bajaj SI below INR 5 lakh after one prior restoration -> NOT_ELIGIBLE because recurrence is exhausted;
- contrast rule triggering claim -> ELIGIBLE when its resolved trigger is satisfied and effective point allows within-claim use;
- contrast rule same-illness subsequent claim -> NOT_ELIGIBLE from its data-only illness rule;
- arbitrary activation expression -> contract rejection;
- overlapping SI bands -> contract rejection.

## Safety property for positive results

A positive eligibility result requires both:

1. a resolved activation-trigger rule; and
2. claim-state evidence that the trigger is satisfied.

If either is unknown, positive eligibility remains unresolved.

A negative triggering-claim result may still be derived when claim-sequence semantics independently rule out use on the triggering claim.

## Explicit exclusions / residue

The gate also preserves current-source exclusions:

- Organ donor expenses: reinstatement/recharge does not apply;
- International Cover — Emergency Care only: reinstatement/recharge cannot be used for payment.

The gate does not resolve or publish:

- restoration amount;
- exact activation trigger;
- same-illness scope while parenthetical scope remains unresolved;
- arbitrary restoration/bonus coupling;
- claim adjudication.

## Gate falsifiers

- any Bajaj fact inherited from a non-current source;
- trigger/activation/availability/consumption collapsed;
- same-claim result marked unknown despite sufficient governed sequence evidence;
- same-claim result inferred without sufficient sequence evidence;
- contrast conformance rule requires evaluator code modification;
- evaluator contains insurer/product identity-bearing branches;
- product data embeds arbitrary executable logic;
- positive eligibility despite unresolved/unsatisfied activation trigger;
- any counterfactual state vector produces an incorrect result;
- unresolved mechanics leak into publication;
- a bounded pass is promoted to arbitrary restoration or claims-adjudication capability.

## Pass conditions

1. Current-source integrity — PASS so far.
2. Semantic preservation across trigger, activation and consumption sequence — PASS so far.
3. Data/logic boundary mechanically tested by second-shape conformance rule — IMPLEMENTED; execution proof pending.
4. Counterfactual execution through one generic evaluator — IMPLEMENTED; execution proof pending.
5. Bounded publication of resolved semantics only — PENDING.

## Claim boundary at closure

A clean Bajaj + contrast-fixture pass may prove that PolicyScna can execute materially different restoration rule shapes without product-specific evaluator code.

It must **not** be described as proof of cross-insurer restoration generalization, arbitrary stateful interactions, copay/restoration ordering, bonus/restoration coupling, or claims adjudication.

## Immediate next action

Run the focused generic restoration-state evaluator tests. If green, inspect whether the resolved/derived bounded mechanics can enter the existing generic certification/publication path without publishing the unresolved activation trigger, restored amount or illness-scope residue.
