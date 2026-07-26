# Engineering Principles

## FEP-001

Never optimize for interfaces before intelligence.

## FEP-002

Every manufactured asset must be evidence-backed.

## FEP-003

Explain. Never manipulate.

## FEP-004

The Factory decides the next manufacturing priority.

## FEP-005

Generic architecture before concept-specific optimization.

## FEP-006

Build once. Manufacture many.

## FEP-007

Every department must pass:

- Manufacturing
- Certification
- Discovery
- Consumption

before it is considered complete.

## FEP-008

Every architectural improvement must be recorded before it is deferred.

## FEP-009

Evidence before explanation.

No product fact, comparison, recommendation, claim guidance, or customer-facing explanation may claim more certainty than its supporting evidence permits.

## FEP-010

Deterministic before AI inference.

Rules, calculations, validation, provenance, product facts, and eligibility logic must be deterministic wherever practical. AI may assist extraction, classification, and explanation, but must not become the source of truth.

## FEP-011

Immutable provenance.

Every manufactured fact and asset must retain traceability to its source document, document version, clause or section, evidence span, extraction path, and validation history.

## FEP-012

Unknown over invented.

When evidence is missing, incomplete, conflicting, unsupported, or not applicable, the Factory must state that clearly and block unsupported conclusions.

## FEP-013

No product-specific hardcoding in Factory core.

Product-specific rules belong in evidence-backed product facts, domain configuration, or approved capability adapters. Exceptions require explicit architectural review and approval by Rajal and the CTO.

## FEP-014

Understanding over answer generation.

A Factory output is successful only when it improves a person’s ability to understand, compare, decide, or act responsibly.

## FEP-015

Reusable capability before one-off implementation.

Every new capability must first be evaluated as a reusable Factory component, concept-family template, domain-pack feature, or evidence contract before custom implementation is approved.

## FEP-016

Truthful system status.

The Factory must keep these states distinct:

- manufactured
- evidence-backed
- illustrative
- runtime-dependent
- blocked
- deprecated

A passing test, generated asset, or successful run must never imply more certainty than the asset’s actual status permits.

## FEP-017

One canonical test contract per production asset.

All executable automated tests must live under the top-level `tests/` directory. Each production asset must have a discoverable owner, an explicit contract, and one canonical verification location.