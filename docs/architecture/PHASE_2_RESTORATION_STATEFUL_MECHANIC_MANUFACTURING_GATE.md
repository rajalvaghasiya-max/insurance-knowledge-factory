# Phase 2 — Restoration Stateful-Mechanic Manufacturing Pressure Gate

**Status:** CERTIFIED AND FROZEN — BOUNDED STATE DERIVATION AND RULE-SHAPE PORTABILITY PROVEN  
**Date:** 2026-08-16

## Purpose

Test whether PolicyScna can manufacture a current-source restoration/reinstatement rule as governed declarative parameters, execute it through an insurer-independent state evaluator, derive claim-sequence consequences from governed source semantics, and publish only the resolved bounded mechanics.

This gate is not a Bajaj restoration subsystem and is not a claims-adjudication engine. It is the first deliberate pressure case where the governed rule describes a state function rather than only a static assertion.

## Primary pressure case

```text
Bajaj General Insurance — My Health Care
UIN: BAJHLIP26074V022526
current governed source SHA-256:
05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
```

All Bajaj restoration propositions in this gate were re-derived from current `05dc...`. Historical Star/Activ One restoration implementations were used only as representation pressure/context, never as current Bajaj truth.

## Current-source qualification

Operative wording on page 17 under `15. Sum Insured Reinstatement` establishes:

```text
reinstated SI use               = subsequent claim
minimum subsequent gap          = 15 days from discharge
other-beneficiary gap exception = yes
covered section                 = Inpatient Hospitalization Treatment
maximum liability per claim     = Inpatient Hospitalization Sum Insured
carry forward                   = no
floater operation               = policy level
individual operation            = insured-beneficiary level
```

Page 52 establishes recurrence bands:

```text
SI < INR 5 lakh  -> once
SI >= INR 5 lakh -> unlimited
```

The page-52 parenthetical `(Available for same illness)` remains scope-sensitive and was not silently promoted into a broad same-illness rule.

Qualification record:

```text
knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/governance/restoration_stateful_mechanic_current_source_qualification.json
```

## Asserted versus derived semantics

The source explicitly states that reinstated SI is available for a **subsequent claim** and normally only after a gap measured from discharge.

The generic evaluator therefore derives:

```text
triggering_claim_can_consume_reinstatement = false
semantic_basis = DERIVED
```

For the headline acceptance scenario:

```text
Base SI                    = INR 10 lakh
single first hospitalization claim = INR 15 lakh
prior restorations         = 0
```

the bounded result is:

```text
REINSTATEMENT_NOT_USABLE_FOR_TRIGGERING_CLAIM_OVERFLOW
```

This conclusion does not decide total claim admissibility, payment, or other benefits.

Governed derivation record:

```text
knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/governance/restoration_triggering_claim_derivation.json
```

## Outcome-C architecture gap found and closed

The repository already contained a governed restoration concept and descriptive mechanic dimensions, but no insurer-independent executable restoration state evaluator.

Current-source pressure therefore justified the smallest generic addition:

```text
insurance_intelligence/benefits/restoration_state.py
```

The evaluator is bounded to closed declarative semantics for:

- claim sequence;
- activation-trigger resolution/satisfaction state;
- activation effective point;
- recurrence bands;
- subsequent-hospitalization gap;
- illness-relationship rule state;
- covered-section scope.

It does **not** calculate claim payment, restored amount, arbitrary expressions, or product-specific algorithms.

## Data/logic boundary — mechanically falsified

The evaluator contains no insurer/product identity branch and does not interpret free-form logic.

A materially different non-product conformance rule executes through the same evaluator unchanged. That contrast shape includes:

```text
activation effective point  = within triggering claim
frequency                   = once
same-illness subsequent use = not allowed
different-illness use       = allowed
one universal SI band
```

The focused suite also rejects arbitrary embedded activation expressions and overlapping SI bands.

This proves **rule-shape portability**, not real cross-insurer restoration generalization.

## Positive-result safety

A positive eligibility result requires both:

1. a resolved activation-trigger rule; and
2. claim-state evidence that the trigger is satisfied.

If either is unresolved, positive eligibility remains unresolved.

A negative triggering-claim result may still be derived when governed claim-sequence semantics independently rule out use on the triggering claim.

## Publication provenance hardening

Stateful publication exposed a second generic governance gap: authoritative publication previously could not distinguish direct source assertions from derived evaluator conclusions.

The authoritative publication semantic-component contract was extended backward-compatibly so that:

```text
semantic_basis = ASSERTED | DERIVED
```

Existing static publication components default to `ASSERTED`.

A `DERIVED` semantic component must carry explicit derivation trace references. This prevents evaluator conclusions from masquerading as literal source wording.

## Generic certification/publication path

The bounded restoration claim-sequence mechanic was certified through the existing generic:

```text
eligibility_and_consequence
```

topic, then passed through the existing generic publication-decision and authoritative-publication gates.

Only bounded claim-sequence semantics were published. The authoritative projection preserves the derived basis of the triggering-claim consequence.

## Explicit unresolved residue

This gate does not resolve or publish:

- exact activation trigger;
- restored amount/percentage;
- exact scope of the same-illness parenthetical;
- different-illness relationship where not independently established;
- bonus participation;
- arbitrary restoration/copay/deductible ordering;
- claim adjudication.

Current-source exclusions also remain explicit:

- Organ donor expenses exclude reinstatement/recharge applicability;
- International Cover — Emergency Care only excludes reinstatement/recharge use for payment.

## Counterfactual and focused execution evidence

Focused state evaluator suite:

```text
7 passed
```

Focused evaluator + asserted/derived publication + bounded Bajaj certification/publication suite:

```text
18 passed
```

Key counterfactuals include:

- Bajaj triggering claim -> NOT_ELIGIBLE for reinstatement consumption;
- Bajaj later claim -> unresolved while activation trigger/scope remain unresolved;
- SI below INR 5 lakh after one restoration -> NOT_ELIGIBLE because recurrence is exhausted;
- contrast rule triggering claim -> ELIGIBLE when its resolved trigger is satisfied and within-claim use is allowed;
- contrast same-illness later claim -> NOT_ELIGIBLE from data-only relationship rule.

## Regression closure

Final local regression evidence reported on 2026-08-16:

```text
insurance_intelligence : 2927 passed
factory_core           : 148 passed
health                 : 124 passed
failures               : 0
```

## Pass conditions

1. Current-source integrity — **PASS**.
2. Semantic preservation across trigger, activation and claim-sequence consumption — **PASS**.
3. Data/logic boundary mechanically tested by second-shape conformance rule — **PASS**.
4. Counterfactual execution through one generic evaluator — **PASS**.
5. Bounded publication of resolved semantics only, with asserted/derived provenance preserved — **PASS**.

## Final certification

**CERTIFIED AND FROZEN.**

This gate proves that PolicyScna can:

- represent a bounded state-dependent insurance mechanic as governed declarative parameters;
- execute materially different restoration rule shapes through one insurer-independent evaluator without product-specific branching;
- derive claim-sequence consequences from governed source semantics;
- preserve `ASSERTED` versus `DERIVED` provenance through authoritative publication;
- fail closed on unresolved activation mechanics;
- publish only the bounded resolved result.

This gate does **not** prove:

- real cross-insurer restoration generalization;
- arbitrary stateful insurance interactions;
- copay/restoration ordering;
- bonus/restoration coupling;
- deductible/restoration ordering;
- general claims adjudication.

A second current-governed insurer restoration rule is required before claiming real cross-insurer restoration generalization.

No further tuning is authorized under this frozen gate.
