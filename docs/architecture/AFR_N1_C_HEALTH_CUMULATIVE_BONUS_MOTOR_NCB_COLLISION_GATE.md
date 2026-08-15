# AFR-N1.C — Health Cumulative Bonus vs Motor NCB Collision Gate

**Status:** CERTIFIED  
**Date:** 2026-08-15

## Certification evidence

```text
AFR-N1.C focused category-collision tests     6 passed
AFR-N1.A + B + C combined                    18 passed
insurance_intelligence                     2886 passed
regressions                                    0
```

## Why this slice exists

The canonical ontology roadmap requires category scoping to be a certified invariant, not an untested naming convention. A dangerous collision exists around bonus terminology:

- Health uses **Cumulative Bonus** for an addition to Sum Insured without an associated premium increase.
- Motor uses **No Claim Bonus (NCB)** for a claim-free benefit and current IRDAI guidance describes its application against Own Damage premium.

The language is close enough that an unscoped glossary or fuzzy resolver could merge the concepts and poison downstream comparison or explanation.

AFR-N1.C therefore pressure-tests the category boundary using primary IRDAI guidance records.

## Source authority

The two records are sourced from current IRDAI guidance pages:

- Health: IRDAI Health Department FAQ 30, under the current 2024 Health framework.
- Motor: IRDAI Motor Insurance — Policy Holder FAQ, under the current General Insurance framework.

These pages are regulator guidance, not regulatory instruments. AFR-N1.C therefore uses the explicit evidence class:

`PRIMARY_REGULATOR_GUIDANCE_SOURCE`

This prevents us from overstating an FAQ as a regulation while still preserving the primary regulator as source authority.

## Semantic decision

AFR-N1.C does **not** register `NCB` as an alias of `health.definition.cumulative_bonus`.

Current IRDAI Health guidance treats No Claim Bonus as broader than Cumulative Bonus: it can be delivered as Cumulative Bonus and/or a renewal-premium discount. Therefore silently equating `NCB` with `Cumulative Bonus` would be incorrect.

For this gate:

```text
Health + "cumulative bonus"
    -> health.definition.cumulative_bonus

Motor + "NCB"
    -> motor.definition.no_claim_bonus

Health + "NCB"
    -> FAIL CLOSED (broader Health NCB concept not yet seeded)

Motor + "cumulative bonus"
    -> FAIL CLOSED
```

The unresolved Health-NCB umbrella is intentional residue, not permission to guess.

## Implementation

### Definition contract refinement

`insurance_intelligence/terminology/standard_definitions.py`

adds:

- `PRIMARY_REGULATOR_GUIDANCE_SOURCE`
- exact governed alias resolution requiring `category + alias + as_of`

No category-free alias resolver is provided.

### Health seed

`insurance_intelligence/terminology/health_regulatory_definition_seed.py`

adds:

`health.definition.cumulative_bonus`

with current IRDAI Health guidance authority.

### Motor pressure seed

`insurance_intelligence/terminology/motor_regulatory_definition_seed.py`

adds:

`motor.definition.no_claim_bonus`

This is a cross-category ontology pressure record only. It does **not** start Motor product onboarding or authorize Motor comparison/recommendation.

## Certified invariants

The focused tests prove:

1. current Health cumulative bonus preserves its Sum Insured meaning;
2. current Motor NCB is a distinct Motor identity;
3. exact alias resolution is category-scoped;
4. Health `NCB` does not silently collapse to cumulative bonus;
5. Motor `cumulative bonus` does not silently map to Motor NCB;
6. cross-category canonical-concept lookup fails closed.

AFR-N1 remains open after this slice. The remaining regression set still needs governed pressure for co-payment conditionality, restoration/recharge semantics, and the remaining approved canonical terms.
