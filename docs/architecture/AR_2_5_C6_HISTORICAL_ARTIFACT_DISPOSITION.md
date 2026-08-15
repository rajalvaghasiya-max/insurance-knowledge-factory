# AR-2.5.C6 — Historical / Generated Intelligence Artifact Disposition

Status: **CERTIFIED — RETAIN THREE FIREWALL FIXTURES; NO C6 DELETIONS**

Audited ref: `feature/mo-028b-health-waiting-period-coverage`

## Scope

C6 audited the legacy generated intelligence output zones:

- `knowledge/health/comparisons/`
- `knowledge/health/recommendations/`
- `knowledge/health/explanations/`

The audit is intentionally conservative. Historical age or generated-file format is not enough to justify deletion.

## Executed evidence

Focused audit tests:

`tests/test_ar25_c6_historical_intelligence_artifact_audit.py`

Result reported by the repository owner: **4 passed**.

Standalone repository audit:

`python scripts/audit_historical_intelligence_artifacts.py`

Result:

- artifacts found: 3
- retained firewall fixtures: 3
- review required: 0

## Retained artifacts

The following files remain intentionally present:

1. `knowledge/health/comparisons/star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison.json`
2. `knowledge/health/recommendations/young_family__star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison_recommendation.json`
3. `knowledge/health/explanations/young_family__star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison_explanation.json`

Each is explicitly inventoried by the governed bypass inventory as an unreachable historical static artifact. Their current value is not insurance truth; their value is executable evidence that historical recommendation-capable artifacts remain outside the certified runtime.

## Authority rule

These artifacts are **HISTORICAL_NON_AUTHORITATIVE**.

They must never be treated as:

- governed facts;
- governed comparisons;
- governed customer decision support;
- recommendation/ranking input;
- current product truth.

They may remain only while they serve bypass/firewall certification or another explicitly approved evaluation purpose.

## Cleanup decision

**No physical deletion is approved under C6.**

Deleting these three artifacts now would remove evidence used by the current bypass inventory and weaken rather than improve repository governance.

Future removal is permitted only after the bypass inventory and its certification tests are intentionally migrated so they no longer depend on the physical fixtures.

## C6 conclusion

The historical output directories contain no uninventoried residue within C6 scope. All present files have an explicit retained-fixture disposition.
