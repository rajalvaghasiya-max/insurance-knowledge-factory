# Phase 2 — Health Intelligence Fitness Review — Bajaj Interaction Falsification Pass

**Status:** ACTIVE REVIEW ARTIFACT  
**Date:** 2026-08-16

## Purpose

Classify current-source Bajaj My Health Care interaction evidence against the Fitness Review falsification outcomes without introducing runtime code or inferring claim-settlement arithmetic that the wording does not explicitly establish.

Current governed source under review:

```text
SHA-256: 05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
UIN: BAJHLIP26074V022526
```

The source review used direct local extraction from the immutable current policy wording.

## Allowed outcomes

- `FOUND_AND_REPRESENTABLE`
- `FOUND_AND_NOT_REPRESENTABLE`
- `FOUND_BUT_AMBIGUOUS_SCOPE`
- `NOT_PRESENT_IN_REVIEWED_CURRENT_SOURCE`
- `SOURCE_REVIEW_INCOMPLETE`

`FOUND_BUT_AMBIGUOUS_SCOPE` must not be promoted to a governed interaction or architecture gate until scope is independently resolved.

---

## Finding B1 — Deductible precedes insurer benefits, but exact capacity-consumption ordering remains ambiguous

Current wording defines Deductible as a cost-sharing requirement under which the insurer is not liable for the specified amount and states that the deductible:

```text
will apply before any benefits are payable by the Insurer
```

It also states:

```text
A deductible does not reduce the Sum Insured.
```

The same principle is repeated for Aggregate Deductible and Per Claim Deductible.

### Review classification

```text
FOUND_BUT_AMBIGUOUS_SCOPE
```

### Why not `FOUND_AND_REPRESENTABLE`

The source clearly establishes a temporal/logical relation between deductible and insurer benefit payment, but the reviewed wording does not independently establish whether this means:

- deductible is applied before determining which capacity bucket is selected;
- deductible is applied after determining admissible expenses but before insurer payment;
- deductible changes restoration-trigger arithmetic;
- deductible changes the amount considered for reinstatement/recharge activation;
- deductible precedes or follows room-rent/proportionate deductions.

Those distinctions materially affect customer questions such as:

> If my claim exceeds the currently available Sum Insured and I also have a deductible, what amount is tested for restoration/reinstatement and when?

The existing ordered-capacity evaluator only chooses among capacity nodes. It does not establish deductible-versus-capacity arithmetic. The current wording is not yet strong enough to authorize such a rule.

### Architecture consequence

```text
NEW ARCHITECTURE GATE: NOT YET JUSTIFIED
```

The missing item is scope/precedence resolution, not proven representational incapacity.

---

## Finding B2 — International Emergency copay explicitly stacks with other copay/deductible

Under International Cover — Emergency Care only, the current wording states:

```text
A mandatory Co-payment of 10% is applicable which will be in addition to any other Co-payment/deductible if any applicable in the policy.
```

### Review classification

```text
FOUND_AND_REPRESENTABLE
```

### Why

This is an explicit composition rule:

- the international-cover 10% copay is not a replacement for another applicable copay/deductible;
- it is additional to them.

This can be represented declaratively as a stacking/applicability relation without deciding monetary settlement order.

### Boundary

This finding does **not** establish the arithmetic sequence among multiple cost-sharing mechanisms. `in addition to` proves cumulative applicability, not necessarily whether one percentage is applied to a pre- or post-deductible amount.

Therefore the following remains unresolved:

```text
COPAY_STACKING_APPLICABILITY = RESOLVED
COPAY_DEDUCTIBLE_ARITHMETIC_ORDER = UNRESOLVED
```

No generic arithmetic/composition evaluator is authorized from this clause alone.

---

## Finding B3 — International Emergency explicitly disables reinstatement/recharge/bonus capacity

The same current-source section states:

```text
Reinstatement, Recharge, Cumulative Bonus, Super Cumulative Bonus,
Major Illness and Accident Multiplier or Double Sum Insured Benefit accrued
cannot be used for payment of claims under International Cover — Emergency Care only.
```

### Review classification

```text
FOUND_AND_REPRESENTABLE
```

### Why

This is a direct exclusion of named capacity mechanisms from a defined benefit scope. It does not require a new interaction engine. It can be represented as a scoped applicability/exclusion relation.

For this cover, restoration-versus-copay ordering is not a live arithmetic question because restoration/recharge/bonus capacity is excluded from payment under the cover.

### Customer-safe conclusion

A customer asking whether reinstatement can supplement an International Emergency claim can receive a bounded source-stated answer that it cannot be used for payment under this cover, subject to confirming the cover and policy instance.

---

## Finding B4 — General coverage clause names SI, limits, deductibles and copayment together but does not order them

The In-patient Hospitalisation scope clause states that indemnity is subject to:

```text
Sum Insured, limits, Deductibles, co-payment, terms, conditions and definitions, exclusions...
```

### Review classification

```text
FOUND_BUT_AMBIGUOUS_SCOPE
```

The list proves co-applicability of multiple constraints but not execution precedence. Section/list order must not be treated as computational order.

---

## Finding B5 — Room-category excess causes proportionate reduction of specified hospital expenses

Current wording states that when admission is in a room category/rate exceeding the opted limit/category, other hospital expenses (with explicit exceptions) are payable in the same proportion as admissible room rate bears to actual room rent.

It separately states that proportionate deductions do not apply in hospitals without differential billing, or to expenses not differentially billed by room category.

### Review classification

```text
FOUND_AND_REPRESENTABLE
```

for the bounded room-linked proportionate-deduction mechanic itself.

However the interaction question:

> Does room-rent proportionate deduction occur before or after copay/deductible/restoration capacity calculations?

is classified:

```text
FOUND_BUT_AMBIGUOUS_SCOPE
```

because the reviewed source does not explicitly establish mutual precedence with those other mechanics.

No monetary ordering may be inferred.

---

## Finding B6 — Voluntary copay uses eligible claim amount payable and remains subject to SI

Current wording for Voluntary Co-payment Discount states that, when opted and a claim is admitted under In-patient Hospitalization Treatment, the insured bears the selected percentage of the:

```text
eligible claim amount payable under this Policy
```

and insurer liability is only in excess of that sum and remains subject to Sum Insured.

### Review classification

```text
FOUND_BUT_AMBIGUOUS_SCOPE
```

### Reason

The clause establishes the copay basis at a high level but does not independently define whether `eligible claim amount payable` is calculated before or after:

- room-category proportionate deduction;
- deductible;
- reinstatement/recharge activation;
- benefit-specific limits.

This wording therefore cannot yet support a generic arithmetic precedence rule.

---

# Falsification result

The current Bajaj source materially strengthens the interaction picture but does **not** yet falsify the working hypothesis that most remaining Health gaps are manufacturing/governance/applicability rather than architecture.

Summary:

| Interaction candidate | Outcome |
|---|---|
| Deductible before insurer benefits vs capacity consumption | `FOUND_BUT_AMBIGUOUS_SCOPE` |
| International 10% copay stacks with other copay/deductible | `FOUND_AND_REPRESENTABLE` |
| International cover excludes reinstatement/recharge/bonus capacities | `FOUND_AND_REPRESENTABLE` |
| General SI/limits/deductible/copay co-applicability | `FOUND_BUT_AMBIGUOUS_SCOPE` |
| Room-category proportional deduction mechanic | `FOUND_AND_REPRESENTABLE` |
| Room deduction vs copay/deductible/restoration precedence | `FOUND_BUT_AMBIGUOUS_SCOPE` |
| Voluntary copay basis vs other mechanics | `FOUND_BUT_AMBIGUOUS_SCOPE` |
| `FOUND_AND_NOT_REPRESENTABLE` | **NONE** |

## Architecture decision

```text
DO NOT OPEN A NEW COMPOSITION EVALUATOR GATE YET.
```

The source proves several explicit interaction facts that can be manufactured declaratively, but the high-harm arithmetic/precedence questions remain scope-ambiguous rather than proven-unrepresentable.

A new architecture gate would become eligible only if a current primary-source clause explicitly resolves one of those mutual precedence relationships and the existing semantic/evaluator contracts then cannot represent/evaluate it without losing a material distinction or adding product-specific executable logic.

## Next review action

1. Manufacture the explicit `FOUND_AND_REPRESENTABLE` Bajaj interaction facts as governed review candidates, without payment arithmetic.
2. Keep all ambiguous precedence questions fail-closed.
3. Complete the same falsification review for Star current wording where scope is still incomplete.
4. Then run the pre-registered restoration-sensitive cross-product comparison; expect incomparability from completeness and/or semantic alignment.

No runtime code is authorized by this artifact.
