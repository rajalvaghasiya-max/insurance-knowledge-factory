# AR-2.5 C4 — Legacy Runtime / Script Firewall

Audit baseline: `feature/mo-028b-health-waiting-period-coverage`

## Purpose

Prevent historical recommendation/comparison utilities from becoming accidental inputs to the current governed PolicyScna runtime while retaining them as historical fixtures and bypass evidence.

## Legacy executable utilities

The following scripts are **HISTORICAL_NON_AUTHORITATIVE** for governed comparison, recommendation, ranking, or decision support:

- `scripts/build_recommendation_context.py`
- `scripts/compare_products.py`
- `scripts/recommend_products.py`

They may remain in the repository for historical tests, anti-pattern evidence, and migration/reference purposes. Their continued presence does not grant architectural authority.

## Enforced boundary

Production Python under:

- `factory_core/`
- `insurance_intelligence/`

must not import, invoke, or reference these legacy utilities or their historical generated output locations.

The sole allowed authoritative reference is:

- `insurance_intelligence/bypass_inventory/classifier.py`

because that module exists specifically to classify the legacy paths and certify their unreachability.

## Historical generated paths covered by the firewall

- `knowledge/health/recommendations/`
- `knowledge/health/comparisons/`
- `knowledge/health/recommendation_contexts/`

These are not admissible governed runtime inputs merely because files exist there.

## Certification

Executable certification:

- `tests/test_ar25_c4_legacy_runtime_firewall.py`
- existing `tests/insurance_intelligence/test_star_bypass_reachability.py`

The firewall is intentionally static and deterministic. It does not delete the legacy utilities or rewrite their historical behavior. A future physical deletion requires a separate cleanup decision proving that their historical/test value is no longer needed.

## Decision

Status: **FIREWALLED / RETAINED AS HISTORICAL EVIDENCE**

New governed development must use current certified knowledge, typed comparison-readiness projections, and governed downstream handoffs. It must not reuse these scripts as runtime architecture.
