# Phase 2 — Activ One Capacity Ordering / Composition Pressure Gate

**Status:** CERTIFIED AND FROZEN  
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

## Certified scope

This gate certifies only bounded capacity-ordering semantics:

1. preserve an ordered capacity chain;
2. distinguish order position from conditional applicability;
3. evaluate which capacity bucket is next eligible for consumption given supplied claim-time state;
4. preserve unresolved/inapplicable capacity without collapsing sequence order;
5. execute a materially different non-product conformance sequence through the same evaluator unchanged;
6. preserve ASSERTED versus DERIVED provenance through generic certification and authoritative publication.

This gate does **not** calculate total payable claim amount, admissibility, copayment, deductible, waiting-period eligibility, room-rent deductions, benefit-limit calculations, or arbitrary cross-benefit claim settlement.

## Current-source semantics

From current Activ One wording:

- Super Reload activates when Base Sum Insured plus accumulated Super Credit, if applicable, is exhausted or insufficient for a claim.
- Super Reload amount is Base Sum Insured and may be available unlimited times during the Policy Year, subject to its conditions.
- Cancer Booster is an optional additional capacity for qualifying cancer claims.
- Capacity order is explicitly Base SI -> Super Credit -> Super Reload -> Cancer Booster.
- Conditional nodes remain conditional: Super Credit and Cancer Booster must not be assumed present merely because they occupy positions in the sequence.

Current-source qualification is materialized at:

```text
knowledge/factory/registry_backed/aditya_birla_health_activ_one/governance/capacity_ordering_current_source_qualification.json
```

## Core semantic separation

```text
ORDER POSITION
!= CAPACITY AVAILABILITY
!= CAPACITY ELIGIBILITY
!= CAPACITY REMAINING AMOUNT
!= CLAIM PAYMENT
```

A node may be correctly positioned in the chain while being unavailable or inapplicable for a particular policy/claim state.

## Architecture result

Repository inspection found descriptive `utilization_sequence` semantics but no insurer-independent executable ordered-capacity traversal primitive.

Current-source pressure justified the smallest generic runtime addition:

```text
insurance_intelligence/benefits/capacity_ordering.py
```

The generic evaluator:

- contains no insurer/product identity branch;
- accepts only a closed ordered-node/state contract;
- separates applicability, availability and capacity state;
- returns only `SELECTED`, `NO_CAPACITY`, or `UNRESOLVED` with traversal trace;
- never calculates monetary claim payment or available amount;
- fails closed when an earlier node's state is unresolved.

## Data/logic boundary

Product/governed data may provide:

- ordered capacity identifiers;
- applicability state for each capacity;
- availability state;
- capacity/exhaustion state;
- governed prerequisites already resolved elsewhere.

Product data must not provide arbitrary expressions such as:

```text
if super_credit > 0 then consume it else call reload(...)
```

Traversal behavior remains generic runtime logic.

## Counterfactual execution proof

The focused evaluator suite proves, among other cases:

- remaining Super Credit is selected before Super Reload;
- exhausted Super Credit allows traversal to Super Reload;
- an optional Cancer Booster can be skipped only when non-applicability is resolved;
- unresolved applicability blocks traversal;
- a materially different neutral capacity chain executes through the same evaluator unchanged;
- no product-specific evaluator code is required.

Focused evaluator result:

```text
7 passed
```

## ASSERTED / DERIVED publication discipline

The source-stated four-node order remains `ASSERTED` from current `38bb...` wording.

Evaluator consequences are governed derivations, including:

- earlier applicable capacity must be resolved as unavailable/exhausted before a later node can be selected;
- unresolved earlier state blocks traversal;
- the selected node is only the next bounded capacity candidate, not a claim-payment conclusion.

The governed derivation is materialized separately from source qualification and referenced by bounded publication as `DERIVED` provenance.

Generic certification/publication artifacts:

```text
knowledge/factory/registry_backed/aditya_birla_health_activ_one/generic_rule_certification/capacity_ordering_certification_case.json
knowledge/factory/registry_backed/aditya_birla_health_activ_one/generic_rule_certification/capacity_ordering_publication_case.json
```

The existing generic `eligibility_and_consequence` topic is reused; no ordering-specific certification topic was introduced.

Focused evaluator + authoritative-publication result:

```text
10 passed
```

## Regression closure

Final local regression evidence supplied on 2026-08-16:

```text
insurance_intelligence : 2942 passed
factory_core            : 148 passed
health                  : 124 passed
failures                : 0
```

No regression required weakening existing contracts or thresholds.

## Pass conditions — final

1. Current-source order anchored only to `38bb...` — PASS.
2. Order, applicability, availability and capacity state represented separately — PASS.
3. One insurer-independent evaluator executes Activ One and a materially different conformance sequence unchanged — PASS.
4. Counterfactual states choose different next capacity nodes correctly — PASS.
5. Unknown applicability fails closed — PASS.
6. No product-specific production reasoning introduced — PASS.
7. Generic certification/publication preserves ASSERTED vs DERIVED provenance — PASS.
8. No claim-payment or whole-product readiness conclusion created — PASS.
9. Broad regressions zero-failure — PASS.

## Certified claim boundary

A clean pass proves that PolicyScna can execute **bounded governed ordered-capacity traversal** from declarative insurer-independent rules and can publish those ordering semantics with source/derivation provenance.

It does **not** prove:

- general claims adjudication;
- arbitrary multi-benefit composition;
- monetary capacity allocation;
- copay/deductible precedence;
- waiting-period/coverage precedence;
- room-rent or benefit-limit ordering;
- all insurance-mechanic interaction rules.

The exact safe claim is:

> Current Activ One evidence plus a materially different conformance rule proves generic ordered-capacity traversal, unresolved-state blocking, and bounded authoritative publication without product-specific evaluator logic. It does not prove a general claim-composition engine.

## Frozen residual / next pressure

The next unresolved architectural question is not capacity order itself. It is **cross-mechanic precedence** where one mechanic changes the state consumed by another, for example copay/deductible interactions or other real current-source composition rules.

No such engine should be built until current governed product evidence creates that pressure.

**Gate result: CERTIFIED AND FROZEN.**
