# Phase 2 — Activ One Capacity Ordering / Composition Pressure Gate

**Status:** ACTIVE — GENERIC ORDERING CONTRACT REQUIRED  
**Date:** 2026-08-16

## Purpose

Test whether PolicyScna can represent and execute a current-governed multi-capacity utilization sequence as declarative insurer-independent data, without turning product wording into executable product logic and without expanding into full claims adjudication.

This gate is driven by current Aditya Birla Health Activ One policy wording anchored to SHA-256:

```text
38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16
```

The current source explicitly states the following utilization sequence:

```text
Base Sum Insured
-> Super Credit (if inbuilt / opted and applicable)
-> Super Reload
-> Cancer Booster (if opted and applicable)
```

The same sequence is stated under both C.10 Super Reload and C.13.10 Cancer Booster.

## Scope

This gate tests only bounded capacity ordering semantics:

1. preserve an ordered capacity chain;
2. distinguish mandatory position from conditional applicability;
3. evaluate which capacity bucket is next eligible for consumption given a supplied state;
4. preserve unresolved/inapplicable capacity without collapsing sequence order;
5. prove rule-shape portability with a materially different non-product conformance sequence;
6. preserve ASSERTED versus DERIVED provenance if publication is reached.

This gate does **not** calculate total payable claim amount, admissibility, copayment, deductible, waiting-period eligibility, room-rent deductions, benefit-limit calculations, or arbitrary cross-benefit claim settlement.

## Current-source semantics

From current Activ One wording:

- Super Reload activates when Base Sum Insured plus accumulated Super Credit, if applicable, is exhausted or insufficient for a claim.
- Super Reload amount is Base Sum Insured and may be available unlimited times during the Policy Year, subject to its conditions.
- Cancer Booster is an optional additional capacity for qualifying cancer claims.
- Capacity order is explicitly Base SI -> Super Credit -> Super Reload -> Cancer Booster.
- Conditional nodes remain conditional: Super Credit and Cancer Booster must not be assumed present merely because they occupy positions in the sequence.

## Core semantic separation

```text
ORDER POSITION
!= CAPACITY AVAILABILITY
!= CAPACITY ELIGIBILITY
!= CAPACITY REMAINING AMOUNT
!= CLAIM PAYMENT
```

A node may be correctly positioned in the chain while being unavailable or inapplicable for a particular policy/claim state.

## Existing architecture pressure

The repository currently contains `utilization_sequence` as a descriptive benefit mechanic. No generic executable capacity-order evaluator was found during repository inspection.

Current-source pressure therefore justifies checking whether the smallest generic closed ordering contract/evaluator is required.

## Data/logic boundary

Product data may provide:

- ordered capacity identifiers;
- applicability state for each capacity;
- remaining-capacity state supplied at evaluation time;
- governed prerequisites already resolved elsewhere.

Product data must not provide arbitrary expressions such as:

```text
if super_credit > 0 then consume it else call reload(...)
```

The generic evaluator must own traversal semantics; product/insurer identity must not determine execution behavior.

## First acceptance scenario

Given the governed Activ One order:

```text
BASE_SUM_INSURED -> SUPER_CREDIT -> SUPER_RELOAD -> CANCER_BOOSTER
```

and claim-time state:

```text
Base SI remaining      = 0
Super Credit applicable= yes
Super Credit remaining = 150,000
Super Reload available = yes
Cancer Booster opted   = yes
```

The generic evaluator must select `SUPER_CREDIT` as the next consumable capacity. It must not skip directly to Super Reload merely because restoration is available.

A second state with Super Credit exhausted must select `SUPER_RELOAD`.

A third state with Cancer Booster not opted must preserve its sequence position but never select it.

## Genericity falsifier

The same evaluator, unchanged, must execute a materially different non-product conformance sequence, for example:

```text
PRIMARY_CAPACITY -> RESTORED_CAPACITY -> BONUS_CAPACITY
```

with different applicability states and still select the correct next eligible node.

If supporting the conformance sequence requires evaluator modification, identity branching, or a product-specific predicate, the gate fails.

## Fail-closed rules

- unknown applicability for the next unresolved node must not be silently treated as false;
- negative/inapplicable state may allow traversal to the next node only when the inapplicability itself is resolved;
- no available amount may be fabricated;
- no absent optional cover may be treated as exhausted;
- no sequence may be inferred from marketing terminology or legacy product implementation;
- historical `d772...` Activ One facts remain non-authoritative for current truth.

## Pass conditions

1. Current-source order remains anchored only to `38bb...`.
2. Order, applicability, availability and amount are represented separately.
3. One insurer-independent evaluator executes Activ One and a materially different conformance sequence unchanged.
4. Counterfactual states choose different next capacity nodes correctly.
5. Unknown applicability fails closed.
6. No product-specific production reasoning is introduced.
7. No claim-payment or whole-product readiness conclusion is created.

## Closure claim boundary

A clean pass may prove that PolicyScna can execute bounded ordered-capacity composition from governed declarative rules.

It must not be described as proof of general claims adjudication, arbitrary benefit composition, copay/deductible ordering, or all insurance-mechanic precedence.

## Immediate next action

Implement the smallest closed insurer-independent ordered-capacity contract/evaluator only if no existing generic runtime primitive already satisfies this pressure; then test Activ One plus the contrast sequence without product-specific branches.
