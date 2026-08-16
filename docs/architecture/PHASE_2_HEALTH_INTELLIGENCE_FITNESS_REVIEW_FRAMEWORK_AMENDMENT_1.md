# Phase 2 — Health Intelligence Fitness Review — Framework Amendment 1

**Status:** ADOPTED — MANDATORY FOR ALL SUBSEQUENT FITNESS REVIEW PASSES  
**Date:** 2026-08-16

## Purpose

Harden the Health Intelligence Fitness Review after independent adversarial review identified ways a source-correct answer could still be unsafe for a real user.

This amendment is architecture-neutral. It does not authorize new runtime code. It changes how review cells are classified, verified, compared, and surfaced to users.

## Core correction

The Fitness Review must evaluate four different questions separately:

```text
Did PolicyScna understand the user's question correctly?
Did PolicyScna produce a source/derivation-correct answer?
Is the answer complete enough for this user's instance?
Can that answer be compared honestly with other products?
```

Therefore:

```text
question interpretation
!= source correctness
!= instance completeness
!= comparability
```

A source-correct answer to the wrong question, or a general conditional answer to an unresolved instance question, is not `ANSWERABLE_VERIFIED`.

---

## Amendment A — Question-shape and instance-variable guard

Every review question must first be classified as exactly one of:

- `GENERAL_SHAPED` — asks what a concept/rule generally means or how it works.
- `INSTANCE_SHAPED` — asks what applies to this customer, policy, claim, hospital, condition, option, date, sum insured, or other concrete state.

For an `INSTANCE_SHAPED` question, the review must identify all load-bearing instance variables before answerability can be graded.

Examples:

### PPN copay

Question:

```text
Will I have a copay?
```

Load-bearing variables include at least:

- whether PPN Discount optional cover is in force for this policy/person;
- whether the treating hospital is inside or outside the applicable PPN;
- any policy-schedule applicability required by the current wording.

Even if the current source rule is perfectly verified, unresolved instance variables cap the result at:

```text
ANSWERABLE_WITH_LIMITATIONS
```

or `BLOCKED`, depending on whether a bounded conditional explanation is safe.

It must not be promoted to `ANSWERABLE_VERIFIED` merely because the generic conditional rule is correct.

### Mandatory rule

```text
INSTANCE_SHAPED
+ unresolved load-bearing instance variable
=> never ANSWERABLE_VERIFIED
```

The unresolved variables must be surfaced explicitly in the limitations/user-safe response.

---

## Amendment B — Harm-stratified verification intensity

Spot-checking is not uniform sampling.

### Harm-floor cells

Every candidate `ANSWERABLE_VERIFIED` cell with `harm_floor = YES` requires a **census check**. No representative sampling is sufficient.

Each such cell must be independently verified before it can become Green.

### Non-harm-floor cells

Representative semantic sampling remains allowed for lower-harm families, provided the sample covers distinct semantic mechanisms rather than only distinct products.

Therefore:

```text
harm_floor = YES
=> every Green candidate checked

harm_floor = NO
=> semantic-stratified sampling permitted
```

Frequency must not reduce verification intensity for a high-harm answer.

---

## Amendment C — Split verification contract for ASSERTED vs DERIVED

`ASSERTED` and `DERIVED` answers require different trust checks.

### ASSERTED verification

Must confirm:

1. current primary/governed source identity;
2. exact current-source proposition;
3. scope/applicability qualifiers;
4. no stale/historical substitution;
5. no semantic broadening beyond the wording.

### DERIVED verification

Must confirm **all ASSERTED verification requirements for every load-bearing input**, plus:

1. exact evaluator/derivation identity/version/reference;
2. explicit state vector used for the tested answer;
3. independent hand-computation or human reasoning of the expected result from those inputs;
4. equality between the hand-computed expected result and evaluator output;
5. no hidden product-specific branch or omitted unresolved state.

A DERIVED result does not become verified merely because its inputs are source-traced.

### Example — Bajaj triggering-claim restoration

The review must not only re-confirm the current wording that reinstated SI is for a subsequent claim. It must also independently reason the specific state:

```text
Base SI = INR 10 lakh
single triggering hospitalization claim = INR 15 lakh
claim sequence = TRIGGERING
activation effective point = SUBSEQUENT_CLAIM_ONLY
```

and confirm that the bounded expected result is:

```text
reinstatement cannot fund INR 5 lakh overflow on that triggering claim
```

before the review marks that DERIVED customer answer verified.

---

## Amendment D — Semantic-alignment comparison guard

Cross-product comparability must now satisfy **two independent gates**:

1. completeness symmetry;
2. semantic alignment.

Comparison states are extended to:

- `COMPARABLE_VERIFIED`
- `COMPARABLE_WITH_LIMITATIONS`
- `INCOMPARABLE_UNTIL_SYMMETRIC`
- `INCOMPARABLE_UNTIL_SEMANTICALLY_ALIGNED`
- `BLOCKED`

### Completeness symmetry

`INCOMPARABLE_UNTIL_SYMMETRIC` applies when decision-relevant governed completeness differs materially across products.

### Semantic alignment

`INCOMPARABLE_UNTIL_SEMANTICALLY_ALIGNED` applies when compared rows use the same business/marketing label but the governed parameter shapes differ materially and have not been normalized to a comparison-safe semantic frame.

Examples include restoration differences in:

- exhaustion versus insufficiency triggers;
- same-triggering-claim versus subsequent-claim use;
- same-illness/different-illness restrictions;
- frequency bands;
- activation effective point;
- covered-section scope;
- recurrence/gap conditions.

Equal completeness does not make semantically different mechanics directly rankable.

The comparison layer must not reduce such differences to a binary `has restoration = yes` field.

---

## Amendment E — Blocked-answer communication contract

Every `BLOCKED` or material `ANSWERABLE_WITH_LIMITATIONS` cell must include:

```text
customer_safe_message
what_is_known
what_is_unresolved
what_would_unblock
```

This prevents fail-closed from becoming fail-silent.

Example for a schedule-delegated PED duration:

```text
what_is_known:
The policy wording states that the applicable PED waiting period is controlled by the Policy Schedule / Product Benefit Table.

what_is_unresolved:
The numeric duration for this customer's policy has not been bound to a governed schedule value.

customer_safe_message:
I cannot safely give you the PED waiting-period number from the policy wording alone. Please provide the Policy Schedule/Product Benefit Table, because that document determines the applicable duration for your policy.

what_would_unblock:
A governed binding to the customer's current Policy Schedule/Product Benefit Table.
```

Silence is not an acceptable blocked-answer behavior on a harm-floor question.

---

## Amendment F — Make the manufacturing-vs-architecture conclusion falsifiable

The working hypothesis remains:

```text
Most remaining Health gaps are manufacturing / governance / applicability gaps,
not new architecture gaps.
```

This is a hypothesis, not a doctrine.

It is falsified when all three conditions hold:

1. a current governed primary-source clause explicitly establishes a consequential interaction/precedence between mechanics;
2. a real high-harm customer/advisor question depends on that interaction;
3. the existing generic semantic/evaluator contracts cannot represent or evaluate it without losing a material distinction or introducing product-specific executable logic.

The next source-review round must actively search for this falsifier rather than only confirming manufacturing gaps.

Allowed falsification outcomes:

- `FOUND_AND_REPRESENTABLE` — manufacturing/governance work; no architecture gate.
- `FOUND_AND_NOT_REPRESENTABLE` — candidate architecture pressure; gate may be justified.
- `NOT_PRESENT_IN_REVIEWED_CURRENT_SOURCE` — no architecture pressure established from that source.
- `SOURCE_REVIEW_INCOMPLETE` — cannot conclude absence.

Search failure alone must never be recorded as `NOT_PRESENT`.

---

## Revised review output fields

### Product-answerability view

Every cell now records:

```text
question_id
question
question_shape = GENERAL_SHAPED | INSTANCE_SHAPED
product
answerability_status
current_source_reference
semantic_basis = ASSERTED | DERIVED | MIXED
asserted_input_references
derivation_reference
instance_variables_required
instance_variables_resolved
limitations
blocker_class
harm_floor
verification_requirement = CENSUS | SAMPLED
spotcheck_status
hand_computation_status
customer_safe_message
what_would_unblock
```

`hand_computation_status` is mandatory for DERIVED harm-floor answers.

### Cross-product comparability view

Every comparison records:

```text
comparison_question_id
products_compared
decision_dimensions
per_product_completeness
semantic_parameter_shapes
completeness_symmetry_status
semantic_alignment_status
comparability_status
asymmetry_or_alignment_reason
safe_comparison_boundary
```

---

## Immediate execution sequence

### Round 1 — verify what is claimed; hunt the architecture falsifier

1. **Bajaj restoration** (`05dc...`)
   - current-source census spot-check;
   - DERIVED state-vector hand check for triggering-claim overflow;
   - instance/general question-shape check.

2. **Bajaj 30-day initial waiting period** (`05dc...`)
   - current-source census spot-check;
   - confirm scope, first-policy commencement, accident exception, continuity exception;
   - do not convert a general source rule into an instance answer without customer continuity/context.

3. **Star conditional copay** (`b1db...`)
   - current-source census spot-check;
   - identify instance variables required to answer `Will this copay apply to me?`;
   - downgrade to limitations if those variables are unresolved.

4. **Falsification search in current Star/Bajaj wording**
   - deductible/coplay versus restoration/reinstatement/capacity;
   - copay versus available/payable amount where precedence is explicit;
   - room-rent/proportionate-deduction interaction with other claim mechanics.

For each candidate, record only one of the four falsification outcomes defined above.

### Round 2 — comparison and fail-safe surface

1. Run at least one real restoration-sensitive comparison through both:
   - completeness symmetry;
   - semantic alignment.
2. Expect incomparability unless both checks pass; this is a successful safety result, not a review failure.
3. Complete `customer_safe_message` and `what_would_unblock` for every harm-floor blocked/limited cell.

---

## Architecture gate authorization rule

No new architecture gate is authorized by this amendment.

A future deductible/copay/capacity interaction gate may open only when current primary wording yields `FOUND_AND_NOT_REPRESENTABLE` for a high-harm real question.

The smallest allowed claim would be:

> one explicitly source-established precedence/interaction between two mechanics can be represented and evaluated as insurer-independent governed data without product-specific branching.

A broader claim such as `arbitrary benefit composition` or `general claims adjudication` is prohibited.

Where possible, a generalization claim requires a second current-governed insurer with a materially contrasting rule shape through the same evaluator.

---

## Non-goals

This amendment does not authorize:

- a new intent/question-understanding runtime subsystem;
- automatic caveat generation;
- comparison productization;
- monetary claim calculation;
- arbitrary interaction/composition engine;
- claims adjudication;
- frontend work;
- Motor or Life expansion;
- database/topology changes.

Question-shape classification is a **review control in this phase**, not a mandate to build new runtime architecture.

## Certification of amendment

**ADOPTED.**

All Fitness Review cells evaluated after this date must apply this amendment before promotion to `ANSWERABLE_VERIFIED` or `COMPARABLE_VERIFIED`.