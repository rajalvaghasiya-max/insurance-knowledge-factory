# Phase 2 — Health Intelligence Fitness Review — Framework Amendment 2

**Status:** ADOPTED — MANDATORY EXECUTION CONTROLS  
**Date:** 2026-08-16

## Purpose

Harden execution fidelity for the Health Intelligence Fitness Review after independent adversarial validation of Framework Amendment 1.

This amendment does not authorize new runtime code. It strengthens how review evidence is logged, how architecture falsification outcomes are classified, how derived checks surface interaction assumptions, and how comparison tests are judged.

---

## Amendment A — Question-shape manual-correction log

Question-shape classification remains a **review control**, not a runtime subsystem.

However, every time the reviewer must manually correct an existing intent/context interpretation from:

```text
GENERAL_SHAPED <-> INSTANCE_SHAPED
```

that event must be logged.

Required fields:

```text
review_case_id
question_text
existing_interpretation
reviewer_corrected_interpretation
load_bearing_difference
would_the_wrong_shape_change_answerability
harm_floor
```

The review must track:

```text
manual_shape_correction_count
harm_floor_manual_shape_correction_count
```

No question-understanding architecture pressure may be asserted from a felt sense that the problem is systematic.

A future runtime pressure case requires recorded evidence that existing intent/context machinery repeatedly misclassifies materially consequential question shape across independent real questions.

---

## Amendment B — Fifth falsification outcome for ambiguous scope

The architecture-falsification vocabulary is expanded to exactly five outcomes:

- `FOUND_AND_REPRESENTABLE`
- `FOUND_AND_NOT_REPRESENTABLE`
- `FOUND_BUT_AMBIGUOUS_SCOPE`
- `NOT_PRESENT_IN_REVIEWED_CURRENT_SOURCE`
- `SOURCE_REVIEW_INCOMPLETE`

### Meaning of `FOUND_BUT_AMBIGUOUS_SCOPE`

Use this when current primary wording contains an apparent interaction/precedence proposition, but a load-bearing term, parenthetical, exception, qualifier, reference, or scope boundary cannot safely be resolved.

Examples include wording whose interpretation depends on unresolved meaning of:

- `admissible claim amount`;
- `available Sum Insured`;
- `subject to` or `after application of` language;
- a parenthetical whose benefit/claim scope is unclear;
- a cross-reference whose operative scope is not yet bound;
- an `unless`, `except`, or schedule-controlled clause that changes precedence.

### Routing rule

```text
FOUND_BUT_AMBIGUOUS_SCOPE
=> scope-resolution / current-source governance work first
=> NOT a governed fact yet
=> NOT an architecture gate yet
```

The result must not be forced into either representable or not-representable merely because the syntactic shape appears to fit an evaluator.

A candidate may move from `FOUND_BUT_AMBIGUOUS_SCOPE` only after the scope question is independently resolved through current governed evidence.

---

## Amendment C — DERIVED verification is also an interaction sensor

A DERIVED hand-computation must explicitly record every semantic assumption required to reach the expected result.

Required fields:

```text
asserted_inputs
state_vector
independent_expected_result
ordering_or_interaction_assumptions_required
assumption_source_status
unresolved_assumptions
```

### Mandatory rule

If the hand-computation requires an ordering or interaction assumption that is not already a governed resolved input, the result cannot be verified by silently baking that assumption into the derivation.

Instead:

```text
unresolved interaction assumption
=> log as falsification-search candidate
=> classify using the five-outcome vocabulary
=> derived cell remains limited/pending as appropriate
```

### Bajaj restoration example

For the bounded question:

```text
Base SI = INR 10 lakh
single triggering hospitalization claim = INR 15 lakh
Can reinstatement fund INR 5 lakh overflow on that same triggering claim?
```

the hand-computation may rely only on the bounded restoration claim-sequence proposition if the result being tested is strictly:

```text
same triggering claim cannot consume reinstated SI
```

It must **not** import or assume copay, deductible, room-rent, or other monetary precedence unless that precedence is required by the proposition being tested.

If a broader monetary conclusion requires such precedence, that dependency becomes a falsification-search finding rather than an implicit derivation input.

This preserves the distinction:

```text
bounded sequence consequence
!= total payable claim calculation
```

---

## Amendment D — Pre-register comparison-test expectations

Every deliberate comparison fitness test must declare its expected safety outcome **before** the result is evaluated.

Required fields:

```text
comparison_test_id
question
products
expected_completeness_gate
expected_semantic_alignment_gate
expected_overall_comparability
reason_for_prediction
unexpected_result_action
```

A test is not validated merely because the framework returns some classification.

### First restoration-sensitive comparison — pre-registered expectation

The first restoration-sensitive comparison across the current Health products is expected to be **incomparable**.

Pre-registered prediction:

```text
completeness symmetry:
EXPECTED TO FAIL unless current review manufacturing has become symmetric across all decision-relevant restoration dimensions.

semantic alignment:
EXPECTED TO FAIL for a naive single-row restoration comparison because governed mechanics differ materially across products in trigger/effective point/claim-sequence and other parameters.

overall:
EXPECTED INCOMPARABLE result via one or both gates.
```

If the comparison unexpectedly returns `COMPARABLE_VERIFIED`, that is an **alarm**, not a success.

Required response to an unexpected comparable result:

1. inspect whether the comparison dimensions were under-specified;
2. inspect whether parameter-shape differences were collapsed into a shared label;
3. inspect whether incomplete product knowledge was treated as absence;
4. do not publish or use the comparison result until the under-triggering question is resolved.

---

## Revised falsification search record

Every searched interaction candidate must now record:

```text
candidate_id
source_sha256
source_page_or_section
interaction_pair
source_proposition
scope_status
falsification_outcome
existing_representation_reference
high_harm_question_dependency
next_action
```

Where `scope_status` is one of:

- `RESOLVED`
- `AMBIGUOUS`
- `REQUIRES_SCHEDULE_OR_CROSS_REFERENCE`
- `NOT_APPLICABLE`

A candidate with `scope_status = AMBIGUOUS` cannot be classified `FOUND_AND_REPRESENTABLE` or `FOUND_AND_NOT_REPRESENTABLE` yet.

---

## Revised Round 1 execution relationship

The review steps are not independent serial stages.

### Step 1 — Bajaj restoration DERIVED census check

This is also a sensor for hidden interaction assumptions.

During the hand-computation:

- record whether the bounded restoration conclusion can be reached without any copay/deductible/capacity-order assumption;
- if yes, state explicitly that those mechanics are outside the tested proposition;
- if no, log the required interaction immediately into the falsification register.

### Steps 2–3 — Bajaj initial wait / Star copay

Apply the same discipline: any load-bearing cross-mechanic assumption encountered during source verification becomes a falsification-search candidate rather than an unrecorded reviewer assumption.

### Step 4 — explicit falsification search

Continue the deliberate current-source search for:

- deductible/coplay versus restoration/reinstatement/capacity;
- copay versus admissible/payable/available amount where precedence is explicit;
- room-rent/proportionate deduction versus other claim mechanics.

Step 4 therefore aggregates both:

```text
interaction candidates discovered during Steps 1–3
+
interaction candidates found by deliberate source search
```

---

## Architecture authorization remains unchanged

No new architecture gate is authorized by finding an interaction clause alone.

A candidate architecture gate still requires:

1. current primary-source evidence;
2. resolved scope;
3. real high-harm question dependency;
4. `FOUND_AND_NOT_REPRESENTABLE` through existing generic contracts;
5. no product-specific executable workaround.

`FOUND_BUT_AMBIGUOUS_SCOPE` explicitly fails condition 2 and cannot authorize architecture.

---

## Non-goals

This amendment does not authorize:

- runtime question-shape classifier work;
- new interaction evaluator;
- claim payment calculation;
- automatic comparison productization;
- automatic caveat generation;
- arbitrary composition engine;
- claims adjudication;
- frontend, Motor, Life, database, or public-launch work.

---

## Execution acceptance criteria

The next Fitness Review round is considered faithful only if:

1. manual question-shape corrections are counted rather than remembered informally;
2. ambiguous-scope interaction clauses are never laundered into representable facts;
3. DERIVED hand-checks expose and log hidden ordering assumptions instead of silently using them;
4. the first restoration comparison has a pre-registered expected incomparability outcome;
5. an unexpectedly comparable result is treated as framework under-triggering until proven otherwise.

## Certification

**ADOPTED.**

Framework Amendment 1 remains in force. This amendment adds mandatory execution controls and must be applied to the next Fitness Review pass before any new `ANSWERABLE_VERIFIED`, `COMPARABLE_VERIFIED`, or architecture-pressure conclusion is accepted.
