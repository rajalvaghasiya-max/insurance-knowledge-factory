# Phase 2 — Health Intelligence Fitness Review — First Pass

**Status:** ACTIVE REVIEW ARTIFACT  
**Date:** 2026-08-16

## Purpose

Run the first question-driven Health fitness pass without adding runtime code. The objective is to separate:

- coverage;
- trustworthiness;
- comparability;
- blocker type;
- harm level.

This artifact is intentionally conservative. A prior certified gate does not automatically make a fitness-review cell `ANSWERABLE_VERIFIED`; a Green answer must be spot-checked against current governed source wording or a current governed derivation trace during this review.

## Status vocabulary

### Answerability

- `ANSWERABLE_VERIFIED` — answer is supported and spot-checked against current governed source / governed derivation in this review.
- `ANSWERABLE_PENDING_SPOTCHECK` — governed machinery appears sufficient, but this review has not yet independently spot-checked the answer against primary current evidence.
- `ANSWERABLE_WITH_LIMITATIONS` — a bounded answer is safe only if material limitations/context requirements are surfaced.
- `BLOCKED` — current governed knowledge/context is insufficient for a safe answer.

### Comparability

- `COMPARABLE`
- `INCOMPARABLE_UNTIL_SYMMETRIC`
- `NOT_A_COMPARISON_QUESTION`

### Blocker class

- `NONE`
- `CURRENT_SOURCE_MANUFACTURING_GAP`
- `POLICY_SCHEDULE_OR_CONTEXT_REQUIRED`
- `UNRESOLVED_SOURCE_SEMANTIC`
- `UNTESTED_INTERACTION_ORDERING`
- `PARTIALLY_PROVEN_INTERACTION_PORTABILITY`
- `PUBLICATION_OR_GOVERNANCE_GAP`
- `SPOTCHECK_REQUIRED`

## Harm floor

Questions are marked `MATERIAL_HARM_FLOOR = YES` where a wrong answer can materially change expected claim funding, out-of-pocket exposure, waiting-period eligibility, or product choice. Such questions are escalated regardless of frequency.

---

# First-pass question matrix

## A. Restoration / capacity

| Question | Star Comprehensive | Bajaj My Health Care | Activ One | Harm floor | Comparability | Review note |
|---|---|---|---|---|---|---|
| Can restoration/reload fund overflow on the same triggering claim? | `BLOCKED` | `ANSWERABLE_PENDING_SPOTCHECK` | `ANSWERABLE_VERIFIED` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | Bajaj is governed/derived as no for triggering claim but primary-source spot-check is still required in this review. Activ One current wording was freshly inspected and supports reload when Base SI + Super Credit are exhausted or insufficient, subject to first-claim restriction and other conditions. Star lacks equivalent current reviewed manufacturing in this fitness pass. |
| Is restoration/reload available for a later claim? | `BLOCKED` | `ANSWERABLE_WITH_LIMITATIONS` | `ANSWERABLE_WITH_LIMITATIONS` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | Bajaj later-claim use is source-governed but positive eligibility remains limited by unresolved activation mechanics. Activ One later claims are supported, but first-claim and schedule/product-benefit-table applicability must be respected. |
| What capacity is used first when multiple capacities exist? | `BLOCKED` | `BLOCKED` | `ANSWERABLE_VERIFIED` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | Activ One current wording explicitly orders Base SI -> Super Credit -> Super Reload -> Cancer Booster. No equivalent current governed multi-capacity chain has yet been established for Star or Bajaj. |

### Restoration/capacity blocker classification

- Star: `CURRENT_SOURCE_MANUFACTURING_GAP` for current restoration/capacity questions in this review.
- Bajaj same-triggering-claim: `SPOTCHECK_REQUIRED`, not an architecture gap.
- Bajaj positive later-claim entitlement: `UNRESOLVED_SOURCE_SEMANTIC` because exact activation mechanics remain unresolved.
- Activ One ordered capacity traversal: `NONE` for the bounded ordering question; general monetary allocation remains out of scope.

## B. Copay / deductible

| Question | Star Comprehensive | Bajaj My Health Care | Activ One | Harm floor | Comparability | Review note |
|---|---|---|---|---|---|---|
| Will a copay apply to this customer/claim? | `ANSWERABLE_PENDING_SPOTCHECK` | `BLOCKED` | `ANSWERABLE_WITH_LIMITATIONS` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | Star conditional copay has prior governed certification but needs fresh source spot-check for this review. Activ One current wording states 10% copay for treatment outside PPN only when the PPN Discount optional cover is in force; policy schedule + hospital context are required. Bajaj current governed product-specific copay applicability has not been established in this pass. |
| Will an opted per-claim deductible reduce available Sum Insured? | `BLOCKED` | `BLOCKED` | `ANSWERABLE_VERIFIED` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | Activ One current wording explicitly states the deductible does not reduce available Sum Insured. The other products are not treated as equivalent by inference. |
| In what order do deductible/copay and capacity consumption apply? | `BLOCKED` | `BLOCKED` | `BLOCKED` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | This is a true interaction-order question. Existing Activ One wording separately establishes deductible, PPN copay and capacity order, but this review has not found current wording establishing their mutual precedence. Do not infer from section order or generic definitions. |

### Copay/deductible blocker classification

- Star conditional copay: `SPOTCHECK_REQUIRED` for the already governed rule.
- Activ One PPN copay applicability: `POLICY_SCHEDULE_OR_CONTEXT_REQUIRED` because optional-cover status and hospital network status are load-bearing.
- Activ One per-claim deductible/SI effect: `NONE` for the narrow source-stated proposition.
- Deductible/copay versus capacity ordering: `UNTESTED_INTERACTION_ORDERING` across the portfolio. This is potential architecture pressure only if current wording from a real product establishes an ordering/interaction that the existing model cannot safely represent.

## C. Waiting periods

| Question | Star Comprehensive | Bajaj My Health Care | Activ One | Harm floor | Comparability | Review note |
|---|---|---|---|---|---|---|
| What is the initial waiting period? | `BLOCKED` | `ANSWERABLE_PENDING_SPOTCHECK` | `ANSWERABLE_PENDING_SPOTCHECK` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | Bajaj has a previously published bounded 30-day initial-wait rule from current source but needs primary-source re-spot-check for this review. Activ One current waiting-period gate identified a 30-day initial wait from current source but did not publish it; therefore it remains pending spot-check/publication review rather than Green. |
| What is the PED waiting period for this policy? | `BLOCKED` | `BLOCKED` | `BLOCKED` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | Activ One normative wording delegates the numeric PED duration to Policy Schedule / Product Benefit Table; no reading-order binding is allowed. No symmetric current governed portfolio fact is available in this review. |
| Does an optional reduction/waiver modify the base waiting period for this customer? | `BLOCKED` | `BLOCKED` | `ANSWERABLE_WITH_LIMITATIONS` | YES | `INCOMPARABLE_UNTIL_SYMMETRIC` | Activ One current source contains reduction and benefit-scoped waiver structures, but selected applicability requires schedule/benefit binding. The semantic model is already sufficient; the remaining problem is applicability/manufacturing, not a new abstraction. |

### Waiting-period blocker classification

- Activ One PED numeric duration: `POLICY_SCHEDULE_OR_CONTEXT_REQUIRED` / `UNRESOLVED_SOURCE_SEMANTIC` from policy wording alone.
- Activ One optional reductions/waivers: `POLICY_SCHEDULE_OR_CONTEXT_REQUIRED`.
- Bajaj initial wait: `SPOTCHECK_REQUIRED`, not architecture pressure.
- Missing symmetric Star/Bajaj facts: `CURRENT_SOURCE_MANUFACTURING_GAP` unless a current governed record already exists and is later surfaced.

---

# Trustworthiness findings

## T1 — Green must be earned twice

The first pass demonstrates why execution success and source trust are separate axes. Bajaj restoration and initial-wait mechanics have passed prior governed pipelines, but this review keeps them `ANSWERABLE_PENDING_SPOTCHECK` until the primary current wording is independently touched again for this review.

This is intentional. Historical certification is evidence of system behavior; it is not a substitute for current fitness-review spot-check evidence.

## T2 — Context-limited can still be source-verified

Activ One provides examples where wording is verified but the customer answer is still not globally Green:

- PPN copay requires the optional PPN Discount cover to be in force and treatment at a non-PPN hospital;
- waiting-period reductions require selected schedule/product-benefit-table applicability;
- Super Reload first-claim use is constrained by Policy Schedule / Product Benefit Table.

Therefore `source verified` does not imply `customer-context complete`.

## T3 — Comparison is currently unsafe for these families

The first pass has no question family where Star, Bajaj and Activ One have symmetric current governed completeness. Consequently all cross-product comparison rows in this artifact are:

```text
INCOMPARABLE_UNTIL_SYMMETRIC
```

This is a governance result, not a product-quality result. It means current knowledge manufacturing is asymmetric and PolicyScna must not turn that asymmetry into a plan ranking.

---

# Architecture versus manufacturing diagnosis

## Manufacturing / governance pressure dominates most cells

Most current blockers are one of:

- current-source manufacturing not yet completed for a product;
- fresh spot-check not yet completed for this review;
- policy schedule / optional-cover / hospital-context binding required;
- unresolved source semantics deliberately preserved.

These do **not** justify new runtime architecture.

## One genuine architecture-pressure candidate remains

The row:

```text
In what order do deductible/copay and capacity consumption apply?
```

is classified:

```text
UNTESTED_INTERACTION_ORDERING
```

However this classification alone does not authorize a new evaluator. A new architecture gate is justified only when current-governed product wording establishes a real interaction/precedence requirement and the existing bounded models cannot safely represent it.

Until then the correct action is source discovery/manufacturing, not code.

---

# Harm-floor priorities

All first-pass questions carry a material harm floor because an incorrect answer can change:

- expected claim funding;
- out-of-pocket exposure;
- waiting-period expectations;
- confidence in product comparison.

Priority therefore does not depend on frequency for safety controls.

For coverage-building order, the first-pass priority is:

1. close source spot-checks for already-governed high-harm answers;
2. manufacture symmetric current facts across Star/Bajaj/Activ One for restoration, copay/deductible and waiting periods;
3. resolve schedule/context applicability where governable;
4. inspect real current wording for deductible/copay versus capacity precedence;
5. open a new architecture gate only if that real wording proves an unrepresentable interaction.

---

# Immediate next action

No new runtime code.

Run primary-current-source spot-checks for the `ANSWERABLE_PENDING_SPOTCHECK` cells, beginning with:

1. Bajaj restoration triggering-claim/subsequent-claim wording (`05dc...`);
2. Bajaj 30-day initial waiting-period wording (`05dc...`);
3. Star conditional copay wording (`b1db...`).

Only after those spot-checks should those cells be eligible for promotion to `ANSWERABLE_VERIFIED`.

In parallel, identify whether Star and Bajaj current governed sources contain explicit deductible/copay versus capacity-order language. Absence is not to be inferred from search failure; it must be recorded as `NOT_YET_ESTABLISHED` until current source review is complete.
