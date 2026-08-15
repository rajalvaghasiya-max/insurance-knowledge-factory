# AR-3.0 — Hostile Commercial Health-Product Pressure Gate

**Status:** CERTIFIED — 2026-08-15

## Purpose

Pressure-test the governed Health knowledge and decision-support architecture against a commercially dense real product without expanding scope or introducing product-specific reasoning. Star Comprehensive was selected because the repository already contained two governed anchors: certified conditional copayment and published automatic restoration.

The gate deliberately used hostile product mechanics to make existing architectural weaknesses visible. A new abstraction was permitted only if real source evidence could not be represented safely by existing generic contracts.

## Certification evidence

Final validation reported on 2026-08-15:

- G5 focused: **6 passed**
- G0–G5 cumulative: **32 passed**
- `tests/insurance_intelligence`: **2868 passed**
- regressions observed: **0**

## Gate outcomes

### G0 — Commercial-product qualification

**CERTIFIED.** Star Comprehensive qualified as a meaningful pressure product using current governed anchors rather than the obsolete snapshot-builder path.

The original G0 defect exposed a wrong certification anchor: an older Star snapshot builder depended on generated/non-retained runtime artifacts. The gate was repaired to use the current certified conditional-copayment path. No production semantics changed.

### G1 — Authoritative evidence inventory

**CERTIFIED.** The immutable registered policy wording was established as the authoritative evidence candidate for additional pressure units. Historical intelligence JSON and the stale coverage audit remain locator/history only and are prohibited as current product truth.

Candidate pressure units identified included:

- 30-day initial illness waiting period
- 24-month specified disease/procedure waiting period
- 36-month PED waiting period
- optional PED waiting-period buy-back
- bariatric surgery limit/waiting interaction
- Delivery and New Born waiting/limit/reset interaction

G1 explicitly did not promote these candidates into governed facts.

### G2 — Atomic normative-unit and residue mapping

**CERTIFIED.** The Delivery and New Born clause was decomposed into separate normative units rather than collapsed into a scalar feature. The represented mechanics included:

- benefit scope
- per-delivery limit rule
- newborn liability limit rule
- 24-month waiting period
- first-commencement anchor
- continuous-renewal condition
- post-claim reset trigger
- post-claim reset effect
- pre-hospitalization exclusion
- post-hospitalization exclusion
- Hospital Cash interaction exclusion

Exact delivery/newborn table values and unreviewed surrounding Section II.14 mechanics remain explicit material residue. No values were invented.

### G3 — Generic semantic-family mapping

**CERTIFIED.** All eleven atomic units could be represented using existing product-agnostic architecture:

- generic semantic facts
- generic relationship facts
- waiting-period semantic effects
- residue accounting
- publication blockers

The post-claim reset was safely represented as a generic trigger/effect relationship pair using `APPLIES_WHEN` plus `MODIFIES`. No Star-specific runtime branch and no new generic contract were required.

### G4 — Cross-family interaction and comparison-readiness pressure

**CERTIFIED.** The pressure slice combined waiting periods, benefit scope, limits, exclusions, benefit interactions, event-triggered reset behavior, and material residue.

The architecture preserved the following invariant:

> Semantic mapping of a represented slice does not imply publication readiness or comparison readiness.

Material unresolved limit/section residue dominated readiness. Therefore publication, comparison, customer-applicability, and net-product-direction outputs remained blocked.

The G4 path also exercised the real generic `ResidueRecord -> PublicationBlocker` contract. Material `DEFERRED_WITH_REASON` residue correctly produced a `MATERIAL_RESIDUE` blocker.

### G5 — Education/decision-support boundary

**CERTIFIED.** Star's unresolved material dimension was bound into the existing MO-027 decision-support path rather than a parallel AR-3.0 response layer.

The certified behavior is:

`NOT_SCORABLE -> UNRESOLVED -> BLOCKED_BY_PRODUCT_UNKNOWN -> ACTION_REQUIRED`

The education layer may explain mapped mechanics and limitations, but it must preserve unresolved findings and must not present a winner, rank, recommendation, suitability conclusion, lean, or net direction. The existing non-verdict boundary remains intact: the projection does not choose a product; the user decides.

## What AR-3.0 proved about the architecture

1. **Real commercial density is representable without product-specific reasoning.** The current generic semantic-fact and relationship-fact contracts handled the selected Star clause, including state/reset behavior.
2. **Atomic decomposition is essential.** A waiting period with continuity, reset, exclusions, and benefit-specific limits cannot safely be reduced to one numeric field.
3. **Residue is a first-class governance object.** Missing exact table rows did not force guessing, silent omission, or premature publication.
4. **Cross-family mapping does not weaken governance.** Even when all represented mechanics were structurally mapped, material unresolved residue still blocked comparison readiness.
5. **The decision-support boundary composes correctly with knowledge uncertainty.** Product unknowns propagate into an action-required education state instead of being converted into a recommendation.
6. **No new generic abstraction was justified by this pressure product.** Existing contracts were sufficient for the tested hostile unit.

## Intentionally unresolved work

The following are not defects in AR-3.0 and were intentionally left unresolved:

- exact Delivery per-event table values by Sum Insured/delivery type
- exact New Born liability table values by Sum Insured
- unreviewed surrounding Section II.14 eligibility/sublimit/event-count/dependent conditions
- G1 candidate pressure units outside the selected Delivery/New Born slice, including PED buy-back, bariatric interaction, and the simpler waiting-period families

These remain blocked from publication/comparison use until separately reviewed and governed.

## Scope boundaries preserved

AR-3.0 did **not**:

- add Star-specific reasoning code
- add a new generic contract without evidence pressure
- promote historical extraction artifacts as truth
- manufacture missing table values
- authorize recommendation or net-product direction
- expand into Motor, Life, frontend, public launch, or unrelated product scope

## Next architecture action

AR-3.0 should now stop. The next action is an **Architecture Fitness Review / checkpoint** over the evidence produced by AR-2.5 and AR-3.0 before opening a new implementation milestone.

That checkpoint should answer only a small set of questions:

1. Which architectural assumptions are now empirically proven by hostile Health-product pressure?
2. Which remaining weaknesses are real blockers versus simply unreviewed product evidence?
3. Does repository topology/ownership still match the intended governed knowledge flow after the recent cleanup and pressure work?
4. Is the current storage/runtime topology still appropriate for the next Health expansion, or has evidence now justified the previously deferred database decision?
5. Which single next Health milestone provides the highest learning value without reopening already-certified architecture?

No frontend, Motor, Life, recommendation expansion, or scale optimization should begin before that checkpoint is closed.

## Final milestone state

**AR-3.0 — CERTIFIED**

The milestone succeeded because it forced a real commercial product through the architecture, preserved uncertainty under pressure, and found no evidence requiring a new product-specific or generic semantic abstraction.