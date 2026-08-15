# AR-3.0.G4 — Star Comprehensive Cross-Family Comparison Readiness Pressure

## Status

**CERTIFIED**

Branch: `feature/mo-028b-health-waiting-period-coverage`

## Certification evidence

- G4 focused: **6 passed**
- AR-3.0 G0–G4 cumulative: **26 passed**
- `tests/insurance_intelligence`: **2862 passed**
- regressions: **0**

## Certified pressure result

The Star Comprehensive Delivery and New Born slice preserves the interaction of:

- benefit scope;
- waiting-period duration and start basis;
- continuous-renewal dependency;
- event-triggered waiting-period restart;
- delivery/newborn benefit limits;
- benefit-scoped expense exclusions;
- Hospital Cash non-applicability;
- explicit material residue.

The represented semantic slice may be structurally mapped while still remaining **not comparison-ready**.

Material unresolved residue dominates softer mapping success:

- publication ready: `false`;
- comparison ready: `false`;
- customer applicability ready: `false`;
- net product direction permitted: `false`;
- decision: `BLOCKED_BY_MATERIAL_RESIDUE`.

The generic `ResidueRecord -> PublicationBlocker` contract is sufficient to preserve the fail-closed state. No Star-specific runtime branch and no new generic contract were required.

## Closure decision

AR-3.0.G4 is certified. G5 may pressure the existing education-first decision-support boundary, but it must not convert unresolved limit residue into an inferred value, complete product assessment, product verdict, ranking, or recommendation.
