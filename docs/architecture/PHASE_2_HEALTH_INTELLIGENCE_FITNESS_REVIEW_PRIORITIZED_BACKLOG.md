# Phase 2 — Health Intelligence Fitness Review — Prioritized Manufacturing Backlog

**Status:** ACTIVE EXECUTION BACKLOG  
**Date:** 2026-08-16

## Purpose

Convert the Fitness Review findings into an execution order that improves safe answerability and honest cross-product comparison without prematurely expanding runtime architecture.

This backlog is constrained by the Fitness Review doctrine:

```text
manufacture / verify / govern first
architecture only on FOUND_AND_NOT_REPRESENTABLE
```

No item below authorizes a new generic evaluator unless its blocker is explicitly reclassified by current-source evidence.

---

## Prioritization rules

Items are ordered by:

1. harm-floor relevance;
2. number of blocked/limited customer questions unlocked;
3. ability to reduce asymmetric comparison coverage;
4. reuse of existing generic semantic/evaluator machinery;
5. architectural consequence only after the above.

High-harm safety gaps are never down-ranked merely because they are less frequent.

---

# P0 — Trust and provenance corrections

## P0.1 — Correct Star conditional-copay lineage semantics

**Question family:** copay applicability  
**Current status:** `ANSWERABLE_PENDING_SPOTCHECK`  
**Blocker:** `CURRENTNESS_OR_LINEAGE_UNVERIFIED`  
**Work type:** GOVERNANCE_CORRECTION  
**Architecture pressure:** NO

### Finding

The governed binding correctly distinguishes:

- current document version anchored to policy wording SHA `b1dbe8fb...`;
- candidate text SHA `ea3aa9a6...`.

The certification module currently places the candidate-text hash into lineage fields named `source_artifact_sha256` and `governed_record_sha256`, creating provenance-label ambiguity even though the reviewed semantic rule itself is current-source based.

### Required action

Inspect the generic evidence/lineage contract and make the smallest governance-correct repair so that:

- source artifact hash means the immutable current source-document hash;
- governed-record hash means the actual governed record hash where required;
- candidate text hash remains a candidate/excerpt hash rather than impersonating source-document identity;
- existing semantics/tests are not broadened.

### Unlock value

Allows the Star conditional-copay rule to be safely re-verified in the Fitness Review.

### Non-goals

- do not change the 10% rule;
- do not alter age-at-entry semantics;
- do not publish the rule merely because lineage is corrected;
- do not create Star-specific production reasoning.

---

# P1 — Symmetric restoration knowledge

## P1.1 — Manufacture current Star Comprehensive restoration/reinstatement semantics

**Question family:** same-claim restoration, later-claim restoration, restoration-sensitive comparison  
**Current status:** `BLOCKED` for Star  
**Blocker:** `CURRENT_SOURCE_MANUFACTURING_GAP`  
**Work type:** MANUFACTURING  
**Architecture pressure:** NO unless current source yields a materially new shape

### Why this is first manufacturing priority

The pre-registered comparison test failed completeness symmetry because Bajaj and Activ One have current governed restoration records while Star does not.

This is currently a knowledge-coverage asymmetry, not evidence that Star has worse restoration.

### Required action

Using current Star source SHA `b1dbe8fb...`:

1. identify the operative restoration/recharge/reinstatement clause, if present;
2. qualify trigger, amount, frequency, same-claim/subsequent-claim timing, same/different illness scope, recurrence/gap conditions, covered sections and exclusions;
3. preserve every unresolved scope explicitly;
4. map to the existing generic restoration model where safe;
5. classify any mismatch under the five falsification outcomes.

### Expected outcomes

Preferred:

```text
FOUND_AND_REPRESENTABLE
```

Possible:

```text
FOUND_BUT_AMBIGUOUS_SCOPE
```

Architecture gate only if:

```text
FOUND_AND_NOT_REPRESENTABLE
```

for a high-harm real question.

### Unlock value

- closes the biggest current restoration comparison asymmetry;
- allows the restoration-sensitive three-product comparison to be re-run on a symmetric completeness basis;
- tests whether semantic alignment remains the only blocker after manufacturing.

---

# P2 — Copay / deductible applicability manufacturing

## P2.1 — Manufacture Bajaj product-specific copay applicability

**Question family:** Will a copay apply to this customer/claim?  
**Current status:** `BLOCKED` in first-pass matrix  
**Blocker:** `CURRENT_SOURCE_MANUFACTURING_GAP` / `MISSING_APPLICABILITY_CONTEXT`  
**Work type:** MANUFACTURING  
**Architecture pressure:** NO

### Current-source evidence already surfaced

Current `05dc...` wording includes at least:

- general co-payment definition;
- 20% copay for non-pre-approved Investigation reimbursement claims;
- mandatory 10% International Emergency copay in addition to other applicable copay/deductible;
- voluntary copayment option at 5% / 10% / 15% / 20% of eligible claim amount payable.

These must remain separate rule shapes and scopes.

### Required action

Manufacture each consequential current Bajaj copay rule separately with:

- trigger;
- scope;
- percentage;
- calculation basis wording;
- optional-cover / plan / reimbursement context;
- interaction statements that are explicit;
- unresolved ordering statements preserved as ambiguous.

### Unlock value

Moves Bajaj from broad `BLOCKED` to a set of scoped customer-safe conditional answers and reduces copay comparison asymmetry.

---

## P2.2 — Manufacture Star deductible / SI-impact facts only if current product source contains them

**Question family:** deductible exposure / available SI  
**Current status:** `BLOCKED`  
**Work type:** SOURCE REVIEW -> MANUFACTURING if present  
**Architecture pressure:** NO

Do not infer from generic definitions that a product-specific deductible exists.

---

# P3 — Waiting-period symmetry

## P3.1 — Manufacture current Star initial waiting-period rule

**Question family:** initial waiting period  
**Current status:** `BLOCKED`  
**Blocker:** `CURRENT_SOURCE_MANUFACTURING_GAP`  
**Work type:** MANUFACTURING  
**Architecture pressure:** NO

### Required action

Use only current `b1dbe8fb...` wording. Preserve:

- duration;
- subject;
- start basis;
- accident exception;
- continuity/migration/portability effect;
- any schedule-selected or optional variation;
- benefit-specific waits separately from base wait.

### Unlock value

Reduces the initial-waiting-period asymmetry versus Bajaj and Activ One.

---

## P3.2 — Complete Activ One 30-day initial-wait governance/publication review

**Question family:** initial waiting period  
**Current status:** `ANSWERABLE_PENDING_SPOTCHECK`  
**Blocker:** `PUBLICATION_OR_GOVERNANCE_GAP`  
**Work type:** VERIFICATION / GOVERNANCE  
**Architecture pressure:** NO

Existing waiting-period semantic model is already sufficient. Do not create new abstraction.

---

## P3.3 — Manufacture Bajaj/Star PED waiting-period applicability only where current authoritative binding permits

**Question family:** PED waiting period for this policy  
**Current status:** `BLOCKED` across current comparison view  
**Work type:** MANUFACTURING / SCHEDULE BINDING  
**Architecture pressure:** NO unless real schedule-binding pressure proves generic model insufficient

Do not import historical numbers or bind table values by reading order.

---

# P4 — Room-rent / proportionate-deduction manufacturing

## P4.1 — Manufacture current Bajaj room-rent consequence as a governed bounded mechanic

**Question family:** What happens if I choose a higher room category?  
**Current source evidence:** current `05dc...` page 9 explicitly states proportional reimbursement of specified hospital expenses when room category exceeds opted limit, with exclusions and a no-differential-billing exception.  
**Work type:** MANUFACTURING  
**Architecture pressure:** NO at first pass

### Guardrail

Do not turn this into claim-payment calculation. Manufacture:

- permitted room category/limit;
- affected expense set;
- excluded expense set;
- proportional basis;
- exception when differential billing is not used;
- any scope boundaries.

### Unlock value

Adds a high-harm financial-exposure answer and prepares a future semantically aligned room-rent comparison.

---

# P5 — Interaction scope-resolution backlog

These are important, but none currently justify runtime expansion.

## P5.1 — Deductible versus restoration/capacity

Current classification:

```text
FOUND_BUT_AMBIGUOUS_SCOPE
```

The deductible wording says it applies before benefits are payable, but reviewed source does not yet establish whether it precedes restoration-trigger testing or capacity selection.

Action: scope-resolution / further source review only.

## P5.2 — Copay versus room-rent / deductible / restoration arithmetic order

Current classification:

```text
FOUND_BUT_AMBIGUOUS_SCOPE
```

Terms such as `admissible claim amount` and `eligible claim amount payable` are not enough to infer full arithmetic precedence.

Action: preserve ambiguity; do not invent sequence.

## P5.3 — International Emergency interaction

Current classification:

```text
FOUND_AND_REPRESENTABLE
```

Current source explicitly states:

- mandatory 10% copay is in addition to other applicable copay/deductible;
- reinstatement/recharge/cumulative-bonus-like capacities cannot be used for this cover.

This is manufacturing/governance work, not architecture pressure.

---

# P6 — Comparison re-runs

Re-run cross-product comparisons only after the relevant decision dimensions have symmetric current governed completeness.

### Restoration-sensitive comparison

Current status:

```text
INCOMPARABLE_UNTIL_SYMMETRIC
AND
INCOMPARABLE_UNTIL_SEMANTICALLY_ALIGNED
```

Next re-run trigger:

```text
Star restoration current manufacturing completed
```

Even then, semantic-alignment failure may remain valid and should not be optimized away.

### Copay comparison

Next re-run trigger:

```text
Star lineage corrected
+ Bajaj product-specific copay rules manufactured
+ Activ One instance-variable requirements retained
```

### Waiting-period comparison

Next re-run trigger:

```text
Star current initial wait manufactured
+ Bajaj verified
+ Activ One governance/spot-check completed
```

---

# Architecture authorization status

At creation of this backlog:

```text
FOUND_AND_NOT_REPRESENTABLE = 0
```

Therefore:

```text
new runtime architecture gates authorized = 0
```

The working hypothesis remains:

> Current Health fitness gaps are dominated by manufacturing, applicability, provenance and governance rather than missing generic runtime architecture.

This remains falsifiable. Any current-source high-harm clause that cannot be represented without semantic loss or product-specific executable logic must be recorded and may reopen architecture pressure.

---

# Recommended execution order

```text
P0.1  Star copay lineage correction
P1.1  Star restoration manufacturing
P2.1  Bajaj scoped copay manufacturing
P3.1  Star initial waiting-period manufacturing
P3.2  Activ One initial-wait governance closure
P4.1  Bajaj room-rent consequence manufacturing
P3.3  PED/schedule-binding work where authoritative evidence permits
P5.x  scope-resolution only as real source evidence warrants
P6.x  comparison re-runs after symmetry prerequisites
```

The sequence is intentionally not driven by code novelty. It is driven by customer harm and comparison-unlock value.

## Immediate next action

Start with **P0.1 — Star conditional-copay lineage correction** because it is a trustworthiness defect in an already-manufactured high-harm rule and should be repaired before investing in additional coverage.
