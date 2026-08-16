# Phase 2 — Activ One Real Cross-Insurer Restoration Portability Gate

**Status:** ACTIVE — CURRENT-SOURCE REVERIFICATION REQUIRED  
**Date:** 2026-08-16

## Purpose

Test whether the generic restoration state evaluator certified in the Bajaj stateful-mechanic gate can execute a second insurer's materially different current-governed restoration rule without evaluator modification, product-specific production reasoning, or reuse of stale product facts.

This gate is the required real-insurer follow-up to the prior Bajaj + synthetic-conformance proof. A successful result may establish real cross-insurer restoration portability for the bounded rule shapes actually exercised. It does not establish arbitrary stateful-composition or claims-adjudication capability.

## Primary pressure case

```text
Aditya Birla Health — Activ One
UIN: ADIHLIP24097V012324
current governed policy-wording SHA-256:
38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16
```

Only the current immutable `38bb...` source may establish product facts in this gate.

## Historical-artifact safeguard

The repository contains a historical Activ One NXT `Super Reload` product implementation anchored to missing policy-wording SHA:

```text
d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451
```

That historical implementation is **not current factual authority**. It may be used only as a search locator and representation-pressure reference.

No historical asserted mechanic may enter current certification unless independently re-derived from `38bb...`.

In particular, historical claims about any of the following start this gate as `UNVERIFIED_AGAINST_CURRENT`:

- restoration/reload percentage;
- unlimited frequency;
- exhaustion-or-insufficiency trigger;
- same-triggering-claim use;
- first-claim use;
- utilization sequence involving Base SI / Super Credit / Super Reload / Cancer Booster;
- covered sections;
- maximum liability per claim;
- any bonus/Super Credit interaction.

## Why this case is selected

Historical representation suggests a materially different rule shape from Bajaj, including possible same-triggering-claim use and a multi-capacity utilization sequence. If the current source independently confirms those semantics, Activ One is a high-value real portability test because it pressures both:

1. restoration evaluator portability across insurers; and
2. possible interaction/ordering semantics between base capacity, bonus-like capacity, restoration capacity, and another booster.

If the current source does not confirm those semantics, the gate must record that honestly and narrow or stop.

## Required current-source inventory

Resolve from `38bb...` in this order:

1. exact benefit name and current variant scope;
2. activation trigger;
3. activation effective point;
4. triggering-claim usability;
5. subsequent-claim usability;
6. restoration/reload amount;
7. frequency/count;
8. first-claim rule;
9. partial restoration/reload use;
10. maximum liability per claim;
11. covered-section scope;
12. utilization sequence / capacity ordering;
13. interaction with Super Credit / cumulative-bonus-like capacity;
14. interaction with Cancer Booster or other capacity mechanics;
15. policy-year reset/carry-forward;
16. floater/member scope;
17. explicit exclusions and unresolved residue.

Missing semantics remain unresolved. No inference by resemblance to the historical implementation.

## Portability falsifier

The existing generic restoration evaluator must remain unchanged for the current Activ One rule shape.

The gate fails portability if current Activ One semantics require:

- insurer/product identity branching in evaluator code;
- a hidden product algorithm encoded as free-form data;
- modification of generic evaluator behavior solely to make Activ One pass without a genuine generic semantic gap.

A generic semantic extension is permitted only if the current source proves a meaning the existing closed vocabulary cannot safely express, and the extension must be insurer-independent.

## Composition boundary

A current-source utilization sequence such as Base SI -> bonus/credit -> reload -> booster, if independently verified, is interaction evidence rather than a scalar benefit fact.

This gate must distinguish:

- **representation of ordering**;
- **evaluation of restoration availability**; and
- **full multi-mechanic claim calculation**.

The first two may be in scope if current evidence supports them. Full claim adjudication is not.

## ASSERTED / DERIVED discipline

Every current Activ One semantic must preserve whether it is directly asserted by `38bb...` or derived through the generic evaluator from current asserted parameters.

Derived outputs must retain the asserted input references and evaluator/derivation trace. Historical `d772...` evidence must never appear as a current evidence reference.

## Pass conditions

1. Current-source integrity: all current Activ One facts derive only from `38bb...`.
2. Stale historical facts remain quarantined unless independently reverified.
3. Materially different current restoration semantics execute through the same generic evaluator without product-specific branching.
4. Counterfactual claim states produce correct bounded results.
5. Any ordering/composition semantics are preserved without collapsing them to a scalar.
6. Publication, if reached, includes only resolved bounded semantics with ASSERTED/DERIVED provenance.
7. No whole-product readiness or arbitrary claims-adjudication inference.

## Immediate next action

Extract all current `38bb...` wording around `Super Reload`, `reload`, `restore`, `restoration`, `Super Credit`, `Cancer Booster`, `exhaust`, `insufficient`, `first claim`, `same claim`, `hospitalization`, `available`, `utilization`, and related capacity-ordering language. Historical `d772...` content may guide search terms only.