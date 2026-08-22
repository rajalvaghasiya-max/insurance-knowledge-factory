# MO-028A Recovery Decision — 2026-08-22

## Decision

Recover the insurer-independent Coverage Registry contracts and deterministic reporting layer from the historical `feature/mo-028a-insurance-intelligence-coverage-registry` branch onto current `main`.

Do **not** recover the historical Health seed or generated Health coverage review as current truth.

## Why

The registry contracts still match the frozen architecture: they inventory what governed insurance intelligence exists for a canonical product/version and expose evidence, lifecycle, concept coverage, comparison readiness, decision-support readiness, and limitations without resolving identity, manufacturing facts, ranking products, or making recommendations.

The historical Health seed predates the current Bajaj v2 currentness and copayment work and therefore represents a stale product snapshot. Reintroducing it unchanged would make historical readiness labels look current.

## Recovery scope

Recovered now:

- `insurance_intelligence/coverage_registry/contracts.py`
- `insurance_intelligence/coverage_registry/reporting.py`
- generic contract regressions
- generic reporting regressions using synthetic registry records only

Explicitly deferred:

- `insurance_intelligence/coverage_registry/health_seed.py`
- `scripts/render_health_coverage_review.py`
- historical generated `HEALTH_INSURANCE_INTELLIGENCE_COVERAGE_REVIEW.md`
- historical MO-028A closure document

## Governance boundary

A fresh Health seed must be manufactured from current governed Star/Bajaj state after this generic foundation is merged. It must not infer lifecycle status, comparison readiness, or decision-support readiness from old snapshots or from product-name knowledge.

No architecture expansion is authorized by this recovery.
