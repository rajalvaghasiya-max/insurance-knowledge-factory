# Phase 2 — Restoration Stateful-Mechanic Manufacturing Pressure Gate

**Status:** ACTIVE — CURRENT-SOURCE DISCOVERY REQUIRED  
**Date:** 2026-08-16

## Purpose

Test whether PolicyScna can manufacture a current-source restoration/reinstatement rule as governed declarative parameters, execute it through an insurer-independent state evaluator, derive claim-sequence consequences from governed timing semantics, and publish only the resolved bounded mechanics.

This is not a request to build a Bajaj restoration subsystem. It is the first deliberate pressure case where the governed rule describes a state function rather than a static assertion.

## Primary pressure case

```text
Bajaj General Insurance — My Health Care
UIN: BAJHLIP26074V022526
current governed source SHA-256:
05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
```

Every Bajaj restoration proposition in this gate must be re-derived from the current `05dc...` source. Historical restoration mappings or legacy product implementations may be reused only as representation pressure/context, never as current product truth.

## Existing architecture that may be reused

The repository already contains a governed restoration concept and mechanic dimensions including restoration percentage/count, trigger requirement/timing, same-hospitalization use, subsequent-hospitalization use, same-illness use, covered-section scope, utilization sequence and policy-year behavior.

Those dimensions are reusable semantic shape. Existing product-specific implementation facts are not automatically reusable evidence.

The current `ProductBenefitImplementation`/`BenefitMechanic` contracts describe product implementations but do not themselves execute claim-state transitions. This gate will first determine whether a narrow generic declarative state-rule contract/evaluator is already present elsewhere; if not, current-source pressure must justify the smallest generic addition.

## Core semantic separation

```text
TRIGGER
!= ACTIVATION EFFECTIVE POINT
!= AVAILABILITY
!= CONSUMPTION ELIGIBILITY
```

The gate must never collapse restoration to a scalar such as `restoration = unlimited`.

## Current-source inventory order

Resolve in this order because claim sequence is more load-bearing than illness relationship:

1. activation trigger;
2. activation effective point;
3. triggering-vs-subsequent claim sequence;
4. restored amount;
5. restoration frequency;
6. Sum Insured band applicability;
7. same-illness subsequent-claim rule;
8. different-illness subsequent-claim rule;
9. exhaustion basis;
10. bonus participation;
11. carry forward;
12. benefit/exclusion scope.

Missing semantics remain explicit residue.

## Derived versus asserted semantics

`triggering_claim_can_consume_restoration` is not presumed to be an independently asserted product field.

Where the source sufficiently establishes activation trigger + activation effective point, the generic evaluator may derive the triggering-claim result from those governed facts and claim sequence state.

Certification/publication must preserve whether an output is:

```text
ASSERTED — directly supported by governed source wording
DERIVED  — produced by the generic evaluator from governed asserted facts
```

If timing evidence is insufficient, same-claim usability remains unresolved; it must not be guessed.

## Non-optional headline acceptance scenario

```text
Base Sum Insured: INR 10 lakh
Single first hospitalization claim: INR 15 lakh
Prior restorations: 0
Question: can restored SI fund the INR 5 lakh overflow on the triggering claim?
```

The answer must be derived from current governed restoration mechanics. A simple subsequent-claim scenario is not sufficient to certify this gate.

## Parenthetical scope safeguard

The table fragment:

```text
Sum Insured Reinstatement
(Available for same illness)
```

is candidate evidence only. It must not automatically certify `same_illness_use = true` until operative wording resolves what the parenthetical modifies.

## Data/logic boundary — mechanical falsifier

A single Bajaj rule cannot prove evaluator independence.

This gate therefore requires a second materially different **non-product conformance rule set** to execute through the same evaluator with zero evaluator modification.

Minimum contrast shape:

```text
activation trigger       = full base-SI exhaustion
activation effective     = after triggering claim settlement
restored amount          = 100% of base SI
frequency                = once
same-illness later claim = not allowed
different-illness later  = allowed
SI bands                 = none
```

This proves rule-shape portability only. It does **not** establish real cross-insurer restoration generalization; a second current governed insurer is required for that later claim.

## Forbidden disguised algorithms

Product data may parameterize a closed generic vocabulary. It must not contain arbitrary executable conditions or product-specific programs.

Forbidden example:

```text
activation_condition = "if exhausted_amount >= base_si and ..."
```

Preferred pattern:

```text
TriggerType / EffectivePoint / FrequencyType / AmountRule / band applicability
```

with closed, insurer-independent semantics and governed parameters.

## Counterfactual execution suite

At minimum the same static governed rule must be evaluated under:

- A — triggering-claim overflow;
- B — subsequent claim after prior exhaustion;
- C — recurrence after restoration already consumed;
- D — SI-band transition where the current source proves a banded frequency rule;
- E/F — same-illness and different-illness subsequent claims only if operative wording resolves those axes.

Different state vectors must produce different outputs where the governed rule requires it.

## Gate falsifiers

- any Bajaj fact inherited from a non-current source;
- trigger/activation/availability/consumption collapsed;
- same-claim result marked unknown despite sufficient governed timing evidence;
- same-claim result inferred without sufficient timing evidence;
- contrast conformance rule requires evaluator code modification;
- evaluator contains insurer/product identity-bearing branches;
- product data embeds arbitrary executable logic;
- any counterfactual state vector produces an incorrect result;
- unresolved mechanics leak into publication;
- a bounded pass is promoted to arbitrary restoration or claims-adjudication capability.

## Pass conditions

1. Current-source integrity.
2. Semantic preservation across trigger, activation and consumption sequence.
3. Data/logic boundary mechanically tested by the second-shape conformance rule.
4. Counterfactual execution through one generic evaluator.
5. Bounded publication of resolved semantics only.

## Claim boundary at closure

A clean Bajaj + contrast-fixture pass may prove that PolicyScna can execute materially different restoration rule shapes without product-specific evaluator code.

It must **not** be described as proof of cross-insurer restoration generalization, arbitrary stateful interactions, copay/restoration ordering, bonus/restoration coupling, or claims adjudication.

## Immediate next action

Inspect the current immutable `05dc...` policy wording for all operative `reinstatement`, `restoration`, `restore`, `sum insured reinstatement`, `same illness`, `exhausted`, `insufficient`, and related claim-sequence language. The page-52 table is not sufficient by itself.
