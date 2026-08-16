# Phase 2 — Health Intelligence Fitness Review Gate

**Status:** ACTIVE — REVIEW FRAMEWORK DEFINED; EXECUTION PENDING  
**Date:** 2026-08-16

## Purpose

Evaluate whether PolicyScna can answer high-value Health customer/advisor questions safely across the currently governed Health portfolio, and identify whether each remaining gap is primarily knowledge manufacturing, current-source verification, applicability/context, cross-product comparability, or genuine architecture pressure.

This review is intentionally **inspect-before-build**. No new runtime capability is authorized merely because a question is blocked.

## Review doctrine

The review must not confuse:

```text
coverage
!= trustworthiness
!= comparability
!= publication readiness
!= whole-product readiness
```

A locally executable answer is not automatically trustworthy, and two locally honest product answers do not automatically compose into an honest comparison.

## Per-question answerability states

Every product × question cell must use exactly one of:

- `ANSWERABLE_VERIFIED` — answer is supported by current governed source / governed derivation and has been source-traced or spot-checked.
- `ANSWERABLE_PENDING_SPOTCHECK` — the governed representation/evaluator can answer, but this specific answer has not yet been independently traced back to current source inputs.
- `ANSWERABLE_WITH_LIMITATIONS` — a bounded answer is safe only when explicit limitations are surfaced.
- `BLOCKED` — safe answer cannot be produced from the current governed state.

`ANSWERABLE_PENDING_SPOTCHECK` is not Green. It exists specifically to prevent an executable but wrong or mis-scoped answer from being silently certified as trustworthy.

## Green spot-check requirement

A review may not declare an answer family trustworthy solely because evaluators/tests execute.

For every question family containing `ANSWERABLE_VERIFIED` cells:

1. at least one representative Green cell per distinct semantic mechanism must be traced to current source wording or a governed derivation built from current-source assertions;
2. any DERIVED result must identify the asserted inputs and evaluator/derivation reference used;
3. stale/historical source anchors must not satisfy current verification;
4. any scope-sensitive wording must remain limited unless its scope is explicitly resolved.

If a cell executes but has not met this check, it remains `ANSWERABLE_PENDING_SPOTCHECK`.

## Confidently-wrong falsifier

The review fails if a cell is marked `ANSWERABLE_VERIFIED` merely because:

- an evaluator returned a result;
- a representation is syntactically complete;
- an old governed implementation contains the same-looking fact;
- a publication exists without current-source lineage being checked;
- a DERIVED result exists without reconstructable asserted inputs.

## Cross-product comparison state

Cross-product comparison is evaluated separately from per-product answerability.

Comparison status must be one of:

- `COMPARABLE_VERIFIED`
- `COMPARABLE_WITH_LIMITATIONS`
- `INCOMPARABLE_UNTIL_SYMMETRIC`
- `BLOCKED`

`INCOMPARABLE_UNTIL_SYMMETRIC` is mandatory when the compared products differ materially in governed completeness for the decision-relevant dimensions, even if individual product cells are locally answerable.

The review must never let missing knowledge masquerade as an inferior policy feature.

Example:

```text
Star restoration mechanics = current, verified
Bajaj restoration mechanics = partial / unresolved
```

This does **not** support a product-quality conclusion. It supports `INCOMPARABLE_UNTIL_SYMMETRIC` for restoration-sensitive comparison.

## Harm floor

Default prioritization for coverage-building work may use:

```text
customer impact × frequency × architectural consequence
```

However frequency may never suppress a high-harm safety gap.

Any question where a wrong answer could plausibly cause material financial, coverage, claim, or medical-planning harm receives a mandatory escalation floor regardless of frequency.

Examples include:

- material copay / deductible exposure;
- restoration availability relied on for a large claim;
- waiting-period / waiver applicability;
- room-rent / proportionate-deduction exposure;
- non-disclosure / eligibility implications;
- comparison claims that could cause a user to choose or reject a product based on asymmetric knowledge.

The harm floor governs **safety priority**. Frequency may still rank **manufacturing order** among equally safe candidates.

## Architecture-vs-manufacturing classification

Every BLOCKED or limited result must identify the smallest blocking cause, not a desired feature.

Allowed blocker classes:

- `MISSING_CURRENT_SOURCE_FACT`
- `CURRENTNESS_OR_LINEAGE_UNVERIFIED`
- `MISSING_APPLICABILITY_CONTEXT`
- `MISSING_POLICY_SCHEDULE_CONTEXT`
- `MISSING_GOVERNED_DERIVATION`
- `MISSING_PUBLICATION`
- `ASYMMETRIC_CROSS_PRODUCT_COMPLETENESS`
- `UNTESTED_INTERACTION_ORDERING`
- `PARTIALLY_PROVEN_INTERACTION_PORTABILITY`
- `REPRESENTATION_GAP`
- `GENERIC_EVALUATOR_GAP`
- `OUT_OF_SCOPE_USER_CONTEXT`

No new subsystem may be proposed until the blocker is stated in one of these terms or an equally precise governed equivalent.

## Interaction taxonomy

The review must distinguish two different classes that must not be conflated:

### A. Untested interaction ordering / composition

Examples:

- copay versus available capacity;
- deductible versus capacity sequence;
- room-rent / proportionate deduction versus other claim mechanics;
- waiting-period rule versus optional waiver where precedence is not yet evaluated.

These may expose a genuine architecture question because the ordering/composition semantics have not yet been proven.

### B. Partially proven portability / manufacturing

Examples:

- Base SI -> Super Credit -> Super Reload -> Cancer Booster ordering for current Activ One is already proven for bounded traversal;
- restoration state evaluation is already proven across current Bajaj and Activ One bounded rule shapes.

A new product expressing similar mechanics is primarily manufacturing/portability pressure unless it introduces a genuinely new semantic shape.

## Initial question families

The first review set should include at minimum:

1. `Q-RESTORE-01` — If my claim exceeds base SI, can restoration/reload fund the same claim?
2. `Q-RESTORE-02` — If restoration is not usable now, when could it become usable?
3. `Q-CAPACITY-01` — What capacity is used first when base SI, bonus/credit, restoration and booster coexist?
4. `Q-COPAY-01` — Does a copay apply to this customer/claim context, and what does that mean?
5. `Q-DEDUCTIBLE-01` — When does a deductible apply and does it reduce available SI?
6. `Q-WAIT-01` — What waiting period applies to this condition/procedure?
7. `Q-WAIT-02` — Does an optional/chronic-care waiver alter the applicable waiting period?
8. `Q-ROOM-01` — What room eligibility/limit applies and what is the consequence of a higher room category?
9. `Q-LIMIT-01` — What benefit-specific sublimit applies to this procedure/benefit?
10. `Q-COMPARE-01` — Which plan is better for a stated customer scenario, and are decision-relevant inputs symmetrically governed?

Additional questions may be added only when they represent a real customer/advisor decision or materially different semantic pressure.

## Review output structure

The review artifact must contain three separate views.

### View 1 — Product answerability matrix

Columns:

```text
question_id
question
product
answerability_status
current_source_reference
derivation_reference
limitations
blocker_class
harm_floor
spotcheck_status
```

### View 2 — Cross-product comparability matrix

Columns:

```text
comparison_question_id
products_compared
decision_dimensions
per_product_completeness
comparability_status
asymmetry_reason
safe_comparison_boundary
```

### View 3 — Prioritized action register

Columns:

```text
action_id
question_id
blocker_class
work_type = MANUFACTURING | VERIFICATION | PUBLICATION | ARCHITECTURE_PRESSURE
harm_floor
frequency
customer_impact
architectural_consequence
recommended_next_action
```

## Review execution rules

1. Start from existing current-governed facts, derivations, certifications and publications.
2. Do not write runtime code during initial review execution.
3. Do not promote legacy intelligence coverage to governed answerability.
4. Do not infer whole-product readiness from selected rule publication.
5. Do not treat `ANSWERABLE_PENDING_SPOTCHECK` as safe Green.
6. Do not produce cross-product recommendations while decision-relevant completeness is asymmetric.
7. Do not rank high-harm wrong-answer risk below frequent low-harm gaps.
8. Do not turn a manufacturing gap into an architecture proposal.
9. Open a new implementation pressure gate only when a real current-source question demonstrates a generic representation/evaluator gap.

## Success condition

The Fitness Review succeeds when it tells us, with evidence, **what PolicyScna can answer safely today, what only appears answerable but still needs source verification, what it cannot safely compare, and which specific missing semantic should be manufactured or pressure-tested next**.

The review is not a success merely because most cells are Green.

## Immediate next action

Build the initial question inventory and evaluate the first three high-harm families against current Star Comprehensive, Bajaj My Health Care and Aditya Birla Activ One governed artifacts, beginning with restoration/capacity, copay/deductible, and waiting-period applicability. No new runtime code is authorized during this first pass.
