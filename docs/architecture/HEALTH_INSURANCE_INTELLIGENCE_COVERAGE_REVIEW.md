# Insurance Intelligence Coverage Review

## Insurer Summary

| Insurer | Products | Lifecycle known | Lifecycle unknown | Comparison-ready products | Decision-support-ready products |
|---|---:|---:|---:|---:|---:|
| aditya_birla_health | 1 | 0 | 1 | 1 | 1 |
| star_health | 1 | 0 | 1 | 1 | 1 |

## Product Coverage

| Insurer | Product | UIN | Lifecycle | Concepts | Certified | Comparison-ready | Decision-support-ready |
|---|---|---|---|---:|---:|---:|---:|
| aditya_birla_health | Activ One NXT | ADIHLIP24097V012324 | STATUS_UNKNOWN | 3 | 1 | 1 | 1 |
| star_health | Star Comprehensive Insurance Policy | SHAHLIP26044V092526 | STATUS_UNKNOWN | 4 | 3 | 3 | 3 |

## Concept Coverage Matrix

| Concept | pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324 | pv_star_health_star_comprehensive_shahlip26044v092526 |
|---|---|---|
| copayment | NOT_COVERED | CERTIFIED |
| restoration | CERTIFIED | CERTIFIED |
| room_rent_restriction | SOURCE_LIMITED | CERTIFIED |
| waiting_periods | NOT_AUTOMATED | NOT_AUTOMATED |

## Coverage Gaps

| Gap | Product | Concept | Status | Explanation |
|---|---|---|---|---|
| CONCEPT_COVERAGE_GAP | pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324 | room_rent_restriction | SOURCE_LIMITED | This publication is sourced from the official insurer product page, not the policy wording.; Proportionate-deduction applicability remains unresolved until exact-UIN policy-wording evidence is governed.; The policy-wording link exposed on the reviewed product page resolved to a different product/UIN and was rejected.; In-force entitlement remains subject to the Policy Schedule, Product Benefit Table, endorsements, and applicable policy wording. |
| CONCEPT_COVERAGE_GAP | pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324 | waiting_periods | NOT_AUTOMATED | Waiting-period semantics have not yet been governed for Activ One NXT decision support. |
| CONCEPT_COVERAGE_GAP | pv_star_health_star_comprehensive_shahlip26044v092526 | waiting_periods | NOT_AUTOMATED | Base initial, specific-disease, and PED waiting-period clauses are not yet governed for automation. |
| LIFECYCLE_STATUS_UNKNOWN | pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324 | - | STATUS_UNKNOWN | Product lifecycle is not yet supported by governed lifecycle evidence. |
| LIFECYCLE_STATUS_UNKNOWN | pv_star_health_star_comprehensive_shahlip26044v092526 | - | STATUS_UNKNOWN | Product lifecycle is not yet supported by governed lifecycle evidence. |
