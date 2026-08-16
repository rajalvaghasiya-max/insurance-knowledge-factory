# Phase 2 — Health Intelligence Fitness Review — Restoration Comparison Test

**Status:** EXECUTED — PRE-REGISTERED INCOMPARABILITY EXPECTATION CONFIRMED  
**Date:** 2026-08-16

## Purpose

Execute the first pre-registered cross-product Fitness Review comparison and verify that the comparison safety gates fail closed when governed completeness is asymmetric and/or nominally similar mechanics are semantically non-equivalent.

This artifact does not rank products and does not calculate claim payment.

## Pre-registered scenario

Customer-shaped question:

```text
I have INR 10 lakh base cover and a single INR 15 lakh hospitalization.
Which of Star Comprehensive, Bajaj My Health Care, or Aditya Birla Activ One gives me the best protection from restoration/reload?
```

Question shape:

```text
INSTANCE_SHAPED
```

Harm floor:

```text
YES
```

The expected review outcome was registered before execution:

```text
comparison should be INCOMPARABLE because completeness symmetry and/or semantic alignment should fail.

If COMPARABLE_VERIFIED is returned, treat it as a framework alarm.
```

## Decision dimensions

The comparison requires, at minimum, governed knowledge of:

- whether restoration/reload can be consumed by the same triggering claim;
- activation effective point;
- activation trigger;
- first-claim restrictions;
- restored amount where needed for a monetary protection conclusion;
- recurrence/frequency;
- relevant claim/benefit scope;
- any prerequisite capacity sequence;
- unresolved conditions that could alter the scenario result.

A simple product-level `has_restoration = yes/no` field is prohibited.

## Per-product governed state

### Star Comprehensive

Current product governance material exists for the current Star Comprehensive source and selected governed semantics, but the current product governance directory does not contain a current governed restoration/reload qualification comparable to the Bajaj and Activ One records used in this test.

Fitness-review state for restoration-sensitive comparison:

```text
completeness = INSUFFICIENT_FOR_THIS_COMPARISON
answerability = BLOCKED
blocker = CURRENT_SOURCE_MANUFACTURING_GAP
```

This is a knowledge-state conclusion, not a conclusion that Star lacks a restoration feature.

### Bajaj My Health Care

Current governed source:

```text
SHA-256 = 05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
```

Current governed restoration mechanics include:

```text
utilization = subsequent claim only
minimum subsequent hospitalization gap = 15 days
other-beneficiary gap exception = yes
frequency at INR 10 lakh SI = unlimited
triggering claim can consume reinstatement = false (DERIVED)
activation trigger = unresolved
restored amount = unresolved
same-illness parenthetical scope = unresolved
```

For the bounded single INR 15 lakh triggering hospitalization on INR 10 lakh base SI:

```text
reinstatement cannot fund the INR 5 lakh triggering-claim overflow
```

This result does not calculate total claim payment or other benefits.

### Aditya Birla Activ One

Current governed source:

```text
SHA-256 = 38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16
```

Current governed Super Reload mechanics include:

```text
activation trigger = Base SI + Super Credit exhausted or insufficient for claim
restored amount = 100% of Base SI
frequency = unlimited during Policy Year
first policy-life claim = not payable, corroborated as from 2nd claim of Policy Life
same-triggering-claim participation = yes when otherwise eligible
utilization sequence = Base SI -> Super Credit -> Super Reload -> Cancer Booster
maximum Super Reload liability per claim = Base SI
```

For the INR 10 lakh / INR 15 lakh scenario, a safe customer-specific conclusion still depends on instance state including at least:

- whether this is the first claim in Policy Life;
- whether Super Credit exists and its available amount;
- whether the claim falls in an eligible covered section;
- other applicable policy conditions.

Therefore the current source supports materially different mechanics from Bajaj but does not by itself justify an unconditional product-ranking answer for the stated customer scenario.

## Gate 1 — Completeness symmetry

Result:

```text
FAIL
```

Reason:

```text
Star restoration/reload is not currently manufactured to a symmetric governed state for this comparison,
while Bajaj and Activ One have current governed restoration records.
```

Comparison status from Gate 1 alone:

```text
INCOMPARABLE_UNTIL_SYMMETRIC
```

This prevents a knowledge-manufacturing deficit from being misrepresented as inferior product protection.

## Gate 2 — Semantic alignment

Result:

```text
FAIL
```

Even ignoring Star's completeness gap, Bajaj and Activ One restoration mechanics are not semantically interchangeable.

Material differences include:

| Dimension | Bajaj My Health Care | Activ One |
|---|---|---|
| triggering-claim use | not usable | usable when otherwise eligible |
| effective point | subsequent claim only | within triggering claim |
| subsequent gap | normally 15 days | no equivalent 15-day rule in governed Super Reload record |
| first-policy-life-claim restriction | not established as this rule shape | explicitly not payable on first claim |
| activation trigger | unresolved | Base SI + Super Credit exhausted/insufficient |
| restored amount | unresolved | 100% Base SI |
| frequency at INR 10 lakh | unlimited | unlimited during Policy Year |
| prerequisite capacity | not established as an ordered stack | Base SI -> Super Credit -> Super Reload -> Cancer Booster |

The shared business label restoration/reload is therefore not a comparison-safe semantic row.

Comparison status from Gate 2:

```text
INCOMPARABLE_UNTIL_SEMANTICALLY_ALIGNED
```

## Final comparison status

Because both comparison safety gates fail:

```text
completeness_symmetry_status = FAIL
semantic_alignment_status = FAIL
comparability_status = INCOMPARABLE
```

The safe customer-facing result is:

```text
I cannot safely rank these three plans from restoration/reload alone yet.
For Bajaj, the current wording supports that reinstatement cannot fund the same triggering claim.
For Activ One, Super Reload works differently and can participate within a later eligible claim once earlier capacity is insufficient, but first-claim and other instance conditions matter.
Star does not yet have symmetrically manufactured current restoration semantics in this review.
Ranking them now would risk comparing our knowledge coverage rather than the policies themselves.
```

## What would unblock a comparison

At minimum:

1. manufacture Star current restoration/reload semantics to the same governed review standard;
2. define a comparison-safe semantic frame that preserves trigger, effective point, first-claim behavior, recurrence, amount, scope and capacity prerequisites rather than collapsing them into a label;
3. provide the customer instance variables required by each product's rule;
4. keep unresolved monetary/payment mechanics out of any ranking dimension until independently governed.

## Framework result

The pre-registered prediction was confirmed.

This is a **successful safety result**, not a product-comparison failure.

An unexpected `COMPARABLE_VERIFIED` result would have indicated that the comparison gates were under-triggering.

## Architecture implication

```text
new architecture gate justified = NO
```

The comparison failure is currently explained by:

- asymmetric current knowledge manufacturing;
- real semantic differences already expressible in governed rule parameters;
- unresolved product facts/context.

It does not demonstrate a generic representation/evaluator gap.

## Guardrails

- Do not conclude which product is better from this artifact.
- Do not infer that Star lacks restoration because the current review lacks symmetric manufacturing.
- Do not flatten Bajaj and Activ One mechanics into `restoration = yes`.
- Do not calculate the INR 15 lakh claim payment.
- Do not infer other capacity/coplay/deductible interactions.
- Do not open a new architecture gate from incomparability alone.
