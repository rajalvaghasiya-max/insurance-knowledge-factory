# AR-3.0.G3 — Star Comprehensive Generic Semantic-Family Mapping

## Status

**CERTIFIED**

Certification evidence:

- G3 focused: `6 passed`
- G0–G3 cumulative: `20 passed`
- `tests/insurance_intelligence`: `2856 passed`
- regressions: `0`

## Certified outcome

The Delivery and New Born G2 atomic units can be mapped into the existing product-agnostic generic-knowledge contracts without adding Star-specific runtime logic or a new generic contract.

The existing architecture is sufficient for this pressure slice because it already supports:

- semantic facts;
- applicability keys;
- relationship facts;
- typed generic relationships including `APPLIES_WHEN`, `MODIFIES`, `DEPENDS_ON`, `INTERACTS_WITH`, and `LIMITED_BY`;
- explicit residue accounting;
- typed fail-closed publication blockers.

The waiting-period concept policy already exposes the semantic effects needed for the represented waiting-period mechanics, including duration, start basis, continuity, applicability, cross-concept relationships, and other normative effects.

## Important representation decision

The post-claim waiting-period restart is not modeled as a Star-specific reasoning rule. It is represented as generic source-anchored semantics:

`claim under Section II.14.A -> APPLIES_WHEN -> reset trigger/effect`

and

`reset effect -> MODIFIES -> 24-month waiting-period rule`

This preserves the event-triggered state transition without introducing insurer/product branching.

## Preserved residue

G3 does not resolve the G2 table-value residue. Exact Delivery and New Born limit table values and any unreviewed surrounding Section II.14 mechanics remain material residue and continue to block limit publication and comparison readiness.

## Architecture decision

No new abstraction is authorized by G3.

Any later abstraction change must be forced by a real pressure unit that cannot be safely represented using the certified generic contracts.
