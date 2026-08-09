# HG-1 — Health Generalization Pilot Selection

## Status

**SELECTED**

This record selects the first multi-product / multi-rule Health generalization pilot to be implemented on top of the certified terminology and entity-resolution baseline.

## Objective

Prove that the governed PolicyScna intelligence architecture is reusable beyond the Star Comprehensive conditional copayment path without importing a later milestone stack wholesale or introducing new architecture unnecessarily.

The pilot must prove all of the following:

1. a second real Health insurer/product identity;
2. a materially different insurance concept from conditional copayment;
3. governed identity and terminology resolution before reasoning;
4. evidence-preserving structured interpretation;
5. fail-closed topic/capability behavior;
6. deterministic explanation with limitations;
7. no Star-specific assumptions in reusable infrastructure.

## Selected pilot

### Product

**Aditya Birla Health Insurance — Activ One / NXT variant**

Canonical product identity target:

- insurer: `aditya_birla_health`
- product: `activ_one`
- target variant: Activ One NXT
- known variant UIN from previously certified governed benefit work: `ADIHLIP24097V012324`

### Concept / benefit

**Restoration of sum insured / Super Reload**

Canonical terminology concept already exists in the MO-024 Health vocabulary as `health:concept:restoration`, with downstream topic `restoration`.

This is materially different from the Star conditional copayment pilot:

- copayment is a claim cost-sharing obligation;
- restoration is a coverage-capacity benefit with activation, frequency, usage, and reset mechanics.

It therefore exercises a different semantic shape and avoids merely proving a second conditional percentage rule.

## Why this candidate was selected

The repository contains later governed work showing that Star Comprehensive and Activ One NXT restoration implementations can be represented using evidence-preserving structured mechanics. That work demonstrates that the concept is technically viable and materially different, but it was built on a later milestone line with a substantially larger test baseline.

This generalization pilot will **not merge that later milestone stack wholesale**. Instead, it will selectively recreate or port only the minimum governed assets needed on top of the current certified branch.

That preserves milestone isolation and lets the pilot answer the architectural question directly: can the current terminology + entity + evidence + reasoning + explanation architecture generalize cleanly?

## Existing reusable foundations on the current certified line

The following foundations are already certified and must be reused rather than duplicated:

- canonical terminology registry and deterministic terminology resolver;
- Health terminology seed containing restoration aliases and customer phrases;
- terminology-to-planner handoff;
- governed runtime product entity resolver;
- insurer-scoped ambiguity handling;
- governed identity-reference adapter;
- entity-to-planner handoff;
- generic reasoning contracts, rule registry, decision gate, and explanation pipeline;
- topic completeness and fail-closed orchestration controls.

## Later work that may be used only as a reference source

Previously implemented MO-025 work contains useful governed restoration structures for:

- Star Comprehensive automatic restoration;
- Activ One NXT Super Reload;
- restoration mechanic normalization;
- evidence-reference preservation;
- factual cross-product comparison.

For HG-1/HG-2 these are **reference implementations**, not automatically authoritative code on this branch. Any reused structure must be deliberately ported, reviewed against the current contracts, and newly certified.

## Pilot execution sequence

### HG-2 — Governed Activ One NXT identity and restoration source audit

Establish the minimum authoritative source/evidence assets needed for the product and restoration benefit. Confirm that the target product/variant identity can enter the new entity-resolution path without ambiguity.

### HG-3 — Restoration topic and semantic contract

Register the restoration topic/capability using existing generic topic infrastructure. Define required semantic outputs for restoration without reusing copayment-specific trigger/obligation assumptions.

Expected restoration mechanics should include only evidence-supported fields such as:

- restoration amount/basis;
- activation trigger;
- activation frequency;
- first-claim availability where stated;
- same-hospitalization/subsequent-hospitalization behavior where stated;
- partial restoration behavior where stated;
- policy-year reset/carry-over behavior where stated.

Missing mechanics must remain unknown or incomplete rather than inferred.

### HG-4 — Evidence-to-reasoning implementation

Create the smallest deterministic rule/output path that converts governed restoration evidence into a typed finding. Do not add comparison, ranking, recommendation, suitability, or claim entitlement logic.

### HG-5 — End-to-end explanation certification

Prove:

`human phrase -> terminology -> product entity -> topic -> evidence -> finding -> decision -> explanation`

for Activ One NXT restoration.

The final explanation must preserve conditions, benefit limits/mechanics, evidence identity, warnings, and any partial-support status.

### HG-6 — Cross-pilot generalization certification

Run both:

- Star Comprehensive conditional copayment; and
- Activ One NXT restoration.

Prove that common infrastructure contains no hard-coded Star/copayment assumptions and that unsupported/missing restoration semantics fail closed.

## Explicit non-goals

This pilot does not implement:

- product ranking;
- product recommendation;
- customer suitability;
- restoration comparison between products;
- MO-025 comparison orchestration;
- generic fuzzy entity matching;
- LLM-based semantic extraction;
- new frontend/API work.

## Closure criteria

The Health generalization pilot is complete only when:

1. Activ One NXT is governed and uniquely resolvable;
2. restoration terminology resolves through the MO-024 layer;
3. the restoration topic uses generic topic/capability contracts;
4. real governed evidence produces a typed restoration finding;
5. the finding reaches a safe explanation with preserved mechanics and limitations;
6. negative/partial cases fail closed;
7. Star conditional copayment remains green;
8. the focused pilot suite passes;
9. the full repository suite passes.

## Decision

**Proceed with Aditya Birla Activ One NXT — Super Reload / restoration as the first multi-product, multi-rule Health generalization pilot.**

The next implementation task is **HG-2 — Governed Activ One NXT identity and restoration source audit**.
