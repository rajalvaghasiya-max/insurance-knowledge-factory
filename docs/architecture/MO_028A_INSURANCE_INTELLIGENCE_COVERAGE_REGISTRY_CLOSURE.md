# MO-028A — Insurance Intelligence Coverage Registry — Closure

## Status

CLOSED

## Purpose

MO-028A established the authoritative internal inventory and review surface for Insurance Intelligence coverage. It answers, deterministically and without inference:

- which insurers are represented;
- which product/version identities are governed;
- each product UIN and lifecycle status;
- which concepts have been processed per product;
- which concepts are certified, partial, source-limited, blocked, not automated, or not covered;
- which concepts are comparison-ready and decision-support-ready;
- where material coverage and lifecycle gaps remain.

The registry is governance infrastructure. It does not resolve product identity, invent product lifecycle, score products, rank products, or recommend products.

## Architecture delivered

### Coverage contracts

`insurance_intelligence/coverage_registry/contracts.py`

Key product lifecycle states:

- `ACTIVE`
- `CLOSED_TO_NEW_BUSINESS`
- `DISCONTINUED`
- `WITHDRAWN`
- `REPLACED`
- `MIGRATED`
- `STATUS_UNKNOWN`

Known lifecycle state requires governed evidence references and a verification timestamp. Where lifecycle evidence is absent, the system fails closed to `STATUS_UNKNOWN`.

Key concept coverage states:

- `NOT_COVERED`
- `DISCOVERED`
- `EVIDENCE_AVAILABLE`
- `NORMALIZED`
- `GOVERNED`
- `CERTIFIED`
- `PARTIAL`
- `SOURCE_LIMITED`
- `BLOCKED`
- `NOT_AUTOMATED`

Decision-support readiness requires comparison readiness and cannot be asserted for unsupported states.

### Initial Health coverage seed

`insurance_intelligence/coverage_registry/health_seed.py`

Initial governed products:

1. Star Health — Star Comprehensive Insurance Policy — UIN `SHAHLIP26044V092526`
2. Aditya Birla Health — Activ One NXT — UIN `ADIHLIP24097V012324`

The seed reuses existing governed runtime product and evidence identities rather than creating a parallel product-truth system.

Current lifecycle for both products remains `STATUS_UNKNOWN` until governed lifecycle evidence is added.

### Deterministic reporting

`insurance_intelligence/coverage_registry/reporting.py`

Generates:

1. insurer coverage summary;
2. product coverage summary;
3. concept coverage matrix;
4. deterministic coverage-gap inventory.

Absent concept coverage is represented explicitly as `NOT_COVERED` in the matrix rather than silently omitted.

### Persisted review artifact

`docs/architecture/HEALTH_INSURANCE_INTELLIGENCE_COVERAGE_REVIEW.md`

The artifact is generated from `HEALTH_COVERAGE_REGISTRY` and can be regenerated with:

```powershell
& C:\Users\rajal\insurance-knowledge-factory\.venv\Scripts\python.exe `
  -m scripts.render_health_coverage_review
```

The renderer is byte-stable across platforms by writing canonical UTF-8/LF output.

## Initial coverage snapshot at closure

### Star Comprehensive

- restoration — `CERTIFIED`
- copayment — `CERTIFIED`
- room-rent restriction — `CERTIFIED`
- waiting periods — `NOT_AUTOMATED`
- lifecycle — `STATUS_UNKNOWN`

### Activ One NXT

- restoration — `CERTIFIED`
- room-rent restriction — `SOURCE_LIMITED`
- waiting periods — `NOT_AUTOMATED`
- lifecycle — `STATUS_UNKNOWN`

## Certification

Focused MO-028A.4 reproducibility/reporting/seed/contracts certification:

- `34 passed`

Full repository certification after MO-028A:

- `2610 passed`
- `0 failed`

Previous authoritative repository baseline before MO-028A:

- `2576 passed`

MO-028A therefore added governed capability and tests without regressing the certified Health Intelligence baseline.

## Architectural invariants preserved

1. Product identity remains governed by the existing product-identity/entity-resolution authority.
2. Lifecycle status is never inferred merely from product age, memory, or stale webpages.
3. `STATUS_UNKNOWN` is preferred over unsupported lifecycle assertion.
4. Concept coverage and readiness are explicit states, not a single ambiguous DONE flag.
5. Source-limited and not-automated concepts remain visible in review output.
6. Registry/reporting does not create insurance facts.
7. Registry/reporting does not score, rank, select, or recommend products.
8. The persisted review artifact is deterministically reproducible from registry state.

## Closure decision

MO-028A is complete and should not be expanded into a generic dashboard/UI project at this stage. Future insurer, product, lifecycle and concept onboarding should update this registry as part of governed certification.

The next roadmap activity should use the registry to drive actual Health knowledge expansion rather than add further registry features.

## Next milestone

MO-028B — Health Concept Coverage Expansion.

Recommended first target: governed waiting-period semantics, because waiting periods are currently explicitly visible as `NOT_AUTOMATED` for both initial products and represent a materially different insurance mechanic from the already-certified copayment, room-rent and restoration capabilities.
