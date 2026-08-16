# Phase 2 — Health Intelligence Fitness Review — Round 1A Bajaj Restoration Census

**Status:** VERIFIED — HARM-FLOOR CENSUS CHECK COMPLETE  
**Date:** 2026-08-16

## Question under review

`Q-RESTORE-01` — If my claim exceeds base Sum Insured, can restoration/reinstatement fund the same triggering claim?

Product:

```text
Bajaj General Insurance — My Health Care
UIN: BAJHLIP26074V022526
current governed policy-wording SHA-256:
05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
```

This is a material-harm question. Verification therefore uses a census check rather than sampling.

## Question shape

The generic proposition is `GENERAL_SHAPED`:

> Can reinstated SI be consumed by the same triggering claim?

A customer-specific monetary question such as:

> My base SI is INR 10 lakh and my hospital bill is INR 15 lakh. Will restoration pay the remaining INR 5 lakh?

is `INSTANCE_SHAPED`, but this review verifies only the bounded restoration-consumption proposition. It does not determine total payable claim amount.

Manual question-shape correction log:

```text
existing runtime misclassification observed = NO EVIDENCE ESTABLISHED IN THIS CHECK
manual reviewer classification performed    = YES
architecture pressure                        = NO
```

One manual review classification is not evidence of systematic runtime inability.

## ASSERTED current-source inputs

Current governed source qualification anchors page 17, Section 15 `Sum Insured Reinstatement` and records the operative wording that:

- reinstated Sum Insured is available for utilization for a **subsequent claim**;
- the subsequent hospitalization normally follows a gap of at least 15 days from discharge;
- the 15-day gap does not apply if the subsequent claim is for another Insured Beneficiary;
- the reinstated SI is scoped to Inpatient Hospitalization Treatment;
- maximum liability per claim remains bounded by the In-patient Hospitalization Sum Insured.

The same qualification explicitly preserves unresolved residue for:

- exact activation trigger;
- restored amount;
- same-illness parenthetical scope;
- different-illness relationship;
- bonus interaction.

No historical Star/Activ One restoration implementation is used as current Bajaj authority.

## DERIVED proposition

Governed derivation:

```text
derivation:bajaj-mhc-restoration:triggering-claim-overflow
```

Asserted input relevant to this bounded result:

```text
activation_effective_point = SUBSEQUENT_CLAIM_ONLY
claim_sequence             = TRIGGERING
```

Expected bounded output:

```text
NOT_ELIGIBLE
TRIGGERING_CLAIM_CANNOT_CONSUME_RESTORATION
```

## Independent hand-computation

Scenario:

```text
base Sum Insured            = INR 10 lakh
single hospitalization bill = INR 15 lakh
claim sequence              = TRIGGERING
restoration use rule        = SUBSEQUENT_CLAIM_ONLY
```

Reasoning:

1. The tested hospitalization is the triggering claim.
2. Current wording restricts reinstated SI utilization to a subsequent claim.
3. A triggering claim is not a subsequent claim.
4. Therefore reinstated SI cannot be consumed by this triggering claim.
5. Consequently the bounded INR 5 lakh overflow cannot be funded **by reinstatement on that same triggering claim**.

Hand-computed expected result:

```text
REINSTATEMENT_NOT_USABLE_FOR_TRIGGERING_CLAIM_OVERFLOW
```

This matches the governed derivation and generic evaluator behavior.

## Interaction-assumption sensor

The hand computation was inspected for hidden assumptions about other claim mechanics.

Required to reach this bounded result:

```text
copay ordering                    = NO
deductible ordering               = NO
room-rent/proportionate deduction = NO
bonus/capacity monetary ordering  = NO
claim-payment calculation         = NO
```

Reason:

`TRIGGERING + SUBSEQUENT_CLAIM_ONLY` is independently dispositive for whether **reinstatement itself** can be consumed by the triggering claim.

Therefore this census check does **not** produce a falsification-search candidate for copay/deductible/room-rent precedence.

If a future question asks the final payable amount on the INR 15 lakh claim, those mechanics may become load-bearing and must be reviewed separately rather than silently imported into this derivation.

## Falsification outcome

For the bounded restoration-consumption question:

```text
FOUND_AND_REPRESENTABLE
```

The current-source semantic is representable by the existing generic restoration evaluator. No new architecture gate is justified.

No `FOUND_BUT_AMBIGUOUS_SCOPE` issue affects the triggering-claim negative result. The separate page-52 same-illness parenthetical remains ambiguous in scope but is not load-bearing for this proposition.

## Fitness Review classification

```text
question_id                    = Q-RESTORE-01
product                        = Bajaj My Health Care
question_shape                 = GENERAL_SHAPED for the certified proposition
semantic_basis                 = DERIVED
harm_floor                     = YES
verification_requirement       = CENSUS
current_source_check           = PASS
asserted_input_check           = PASS
derivation_trace_check         = PASS
hand_computation_status        = PASS
hidden_interaction_assumption  = NONE REQUIRED
answerability_status           = ANSWERABLE_VERIFIED
blocker_class                  = NONE for the bounded same-triggering-claim proposition
```

## Customer-safe boundary

Safe statement:

> Under the current My Health Care wording, reinstated Sum Insured is for a subsequent claim, so it cannot be used to fund overflow on the same triggering hospitalization.

Required limitation:

> This does not determine the total amount payable on that hospitalization. Other policy mechanics, admissibility rules, limits, copay, deductible, room-rent consequences, or other benefits may affect the final claim outcome and are not resolved by this restoration-only result.

## What remains unresolved

This verification does not promote or resolve:

- exact restoration activation trigger;
- restored amount;
- positive later-claim restoration eligibility where the activation trigger remains unresolved;
- same-illness parenthetical scope;
- different-illness rule;
- bonus interaction;
- arbitrary claim-payment ordering.

## Review conclusion

`Q-RESTORE-01` for Bajaj My Health Care is promoted from `ANSWERABLE_PENDING_SPOTCHECK` to `ANSWERABLE_VERIFIED` **only for the bounded proposition that reinstatement cannot fund the same triggering claim**.

The result required no hidden interaction-order assumption and therefore does not create new architecture pressure.
