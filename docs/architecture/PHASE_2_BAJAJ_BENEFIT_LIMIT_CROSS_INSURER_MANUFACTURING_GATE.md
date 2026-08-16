# Phase 2 — Bajaj Benefit-Limit Cross-Insurer Manufacturing Gate

**Status:** ACTIVE — CURRENT-SOURCE CANDIDATE QUALIFICATION REQUIRED  
**Date:** 2026-08-16

## Purpose

Prove that a second insurer's simple benefit-specific monetary limit can travel through PolicyScna's existing generic Health knowledge-manufacturing path without Bajaj-specific production reasoning or a new semantic abstraction.

This gate continues the manufacturing proof after the certified Bajaj initial waiting-period gate. It does not expand product scope or create a new subsystem.

## Why benefit limits now

MO-028C already established the architectural pressure and final design for Health benefit-limit/sub-limit semantics. Its Star Arogya qualification found the semantic family representable after generic hardening, but the committed qualification explicitly did not certify the real-product mapping.

The current generic topic catalogue also already provides the insurer-independent `coverage_limit` topic with:

- `covered_subject`
- `limit_value`
- `limit_basis`
- `applicability_scope`
- optional `excess_consequence`

Therefore the next pressure should be manufacturing against a real second-insurer rule, not more ontology design.

## Candidate pressure case

Candidate product:

```text
Bajaj Allianz General — My Health Care
UIN: BAJHLIP26074V022526
current source SHA-256: 05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158
```

Candidate semantic family:

```text
simple benefit-specific monetary limit
```

`Family Visit` is a search candidate because earlier current-source parsing pressure exposed benefit-limit-shaped wording around that benefit. This gate does **not** assert that Family Visit is the final rule, amount, period basis, or publishable semantic proposition until the current `05dc...` source is inspected directly.

If Family Visit is schedule-bound, table-order dependent, ambiguous, interaction-heavy, or otherwise unsuitable for a bounded first proof, another simple current-source Bajaj benefit limit may be selected instead. The reason must be recorded; values must never be guessed.

## Existing architecture to reuse

The gate must prefer existing generic contracts already present in the repository:

1. current governed source identity/currentness;
2. generic evidence representation;
3. `coverage_limit` topic completeness;
4. generic rule certification;
5. generic publication-decision evaluation;
6. generic authoritative-publication gate.

MO-028C design artifacts are architectural guidance and historical pressure evidence. They must not be treated as current Bajaj product facts.

## Gate sequence

1. Verify the local immutable Bajaj current PDF hash is exactly `05dc...`.
2. Search the current source for a simple benefit-specific monetary limit, starting with `Family Visit`.
3. Capture enough bounded current-source context to resolve, without inference:
   - covered subject;
   - limit value;
   - currency/unit;
   - limit basis/period;
   - applicability scope;
   - excess consequence if explicitly present;
   - material cost-sharing or schedule interaction if explicitly present.
4. Reject the candidate for this gate if required semantics depend on table reading order, an unresolved schedule/band binding, or an unstated assumption.
5. Materialize current-source governed evidence only after the proposition is resolved.
6. Use the existing generic `coverage_limit` topic and rule-certification runner.
7. Use existing generic publication decision and authoritative publication only if certification and governance boundaries permit it.
8. Keep all unrelated Bajaj benefit limits/residue unresolved.
9. Run focused and broader regressions.

## Acceptance criteria

- current immutable source SHA `05dc...` is the only current factual authority;
- no historical mapping is silently promoted as current truth;
- selected rule is genuinely benefit-specific and bounded;
- covered subject, value, basis and applicability are explicitly evidenced;
- no table-order guessing or schedule/band inference;
- no scalar flattening that drops material exceptions/interactions;
- zero Bajaj-specific production reasoning code;
- no new semantic abstraction unless current-source pressure proves an actual generic gap;
- generic `coverage_limit` contract reused if adequate;
- certification/publication limited to the selected rule only;
- unrelated benefit-limit residue remains explicit;
- no whole-product governed-readiness inference;
- regressions remain green.

## Current conclusion

The benefit-limit semantic family is the correct next cross-family manufacturing pressure, but no Bajaj monetary-limit fact is approved by this gate yet. Current-source candidate qualification is the next required action.
