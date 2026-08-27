# Insurance Intelligence — Instance Sufficiency Guard v1

**Status:** bounded hardening slice after Assertion / Advisory Boundary closure.

## Audit verdict

MO-014 Context Builder is reused as-is. Its governed requirement registry, provenance model, conflict handling, assumptions, completeness, answerability, and clarification behavior remain unchanged.

The identified gap is instance identity: Context Builder may carry a user-provided or system-derived product/policy/document reference, but explicitly does not establish authoritative identity. A textual/candidate reference therefore cannot by itself authorize instance-specific planning.

## Purpose

The Instance Sufficiency Guard sits between Context Builder and Reasoning Planner. It requires a governed instance-resolution attestation for intents whose reasoning depends on a specific product, policy, quote/document, or comparison subject.

It does not resolve names, infer UINs, read product documents, access target insurance semantics, retrieve evidence, or reason about coverage.

## Reuse boundary

Instance resolution is an upstream governed capability. This guard consumes attestations shaped around the existing Knowledge Factory identity discipline:

- explicit canonical identity;
- immutable identity-record reference;
- identity-record hash;
- explicit resolution status;
- fail-closed ambiguity/unresolved states.

The guard does not import `factory_core` or mutate Knowledge Factory identity records.

## Core invariant

> A mention is not an identity.

`USER_PROVIDED` or `SYSTEM_DERIVED` context may prove that the user referred to a product/policy/document, but instance-specific planning is authorized only when the corresponding context key has a `RESOLVED` governed attestation.

`AMBIGUOUS` and `UNRESOLVED` never degrade to a best-match identity.

## v1 required-instance policy

The following intents require governed instance resolution before Planning:

- `POLICY_FACT_LOOKUP`
- `POLICY_SUMMARY`
- `COVERAGE_CHECK`
- `EXCLUSION_CHECK`
- `CLAIM_SCENARIO`
- `PRODUCT_EXPLANATION`
- `PRODUCT_COMPARISON`
- `POLICY_COMPARISON`
- `QUOTE_COMPARISON`
- `DOCUMENT_INTERPRETATION`
- `SUITABILITY_ASSESSMENT`

`CLAUSE_IMPLICATION` is conditional: a generic clause explanation may proceed without a product/policy instance, but once a specific product/policy reference is present, that reference must resolve before instance-specific planning.

Concept-level requests such as `TERM_EXPLANATION` do not require an instance.

## Upstream exits

The guard preserves upstream exits:

- `OUT_OF_SCOPE` remains out of scope;
- `CLARIFICATION_REQUIRED` remains a clarification exit;
- `NOT_ANSWERABLE` and `PARTIALLY_ANSWERABLE` do not authorize Planning in v1.

The guard does not weaken Assertion / Advisory obligations and does not authorize recommendation execution.

## Scope exclusions

This milestone does not build a runtime product-name resolver, policy-document resolver, UIN matcher, recommendation engine, suitability engine, evidence resolver, or new Context Builder logic. It adds only the governed attestation contract and deterministic sufficiency decision.

## Acceptance criteria

- MO-014 source files unchanged;
- no fuzzy or best-match identity inference;
- system-derived candidate text alone cannot satisfy identity;
- all required comparison subjects must resolve independently;
- ambiguous/unresolved identities fail closed;
- instance-insensitive requests may proceed without an attestation;
- planning authorization emitted only for `PASS`;
- no recommendation authorization or semantic insurance reasoning introduced.
