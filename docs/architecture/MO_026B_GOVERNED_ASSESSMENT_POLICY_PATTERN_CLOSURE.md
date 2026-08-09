# MO-026B Governed Assessment Policy Pattern — Closure

## Status

**CLOSED**

## Objective

Establish a governed, deterministic, education-first policy mechanism that can classify one insurance benefit dimension on its own terms without introducing cross-benefit weighting, aggregate product scores, ranking, suitability, or recommendation.

## Certified pattern

The first certified policy covers the Health restoration dimension.

The pattern consists of:

1. `BenefitAssessmentPolicy` — versioned governed policy contract.
2. Explicit required mechanic identities.
3. Deterministic band rules with rationale and explanation text.
4. Approved/published/effective-date governance.
5. `assess_product_benefit` — deterministic policy evaluator.
6. Evidence and mechanic lineage preservation.
7. Fail-closed `NOT_SCORABLE` behavior when required mechanics are missing or no published rule matches the governed mechanic combination.

## Certified restoration outcomes

- Aditya Birla Health Activ One NXT / Super Reload → `VERY_STRONG` on intrinsic restoration mechanics.
- Star Health Star Comprehensive / Automatic Restoration → `STRONG` on intrinsic restoration mechanics.
- Missing required restoration mechanics → `NOT_SCORABLE`.
- Materially different or unrecognized restoration mechanic combinations → `NOT_SCORABLE`.

These outcomes describe the intrinsic restoration mechanics only. They are not overall product ratings and do not imply customer suitability or recommendation.

## Important defect found and resolved during certification

The initial restoration policy included an overly broad `MODERATE` fallback rule based only on the presence of a restoration percentage and trigger. A certification case changed Activ One NXT to a 50% restoration with no subsequent-hospitalization use and demonstrated that this unsupported combination was still receiving an assessment band.

The failing test was preserved. Production policy rules were tightened so that v1 recognizes only mechanic signatures that are currently certified. Unsupported combinations now fail closed as `NOT_SCORABLE`.

This establishes an important MO-026 rule: **absence of a matching governed assessment policy is not permission to infer a qualitative band.**

## Certification evidence

Focused regression after the fail-closed correction:

- **48 passed**
- `tests/insurance_intelligence/test_mo026b_governed_assessment_policies.py`
- `tests/insurance_intelligence/test_mo026a_benefit_assessment_contracts.py`
- `tests/insurance_intelligence/test_mo026a_assessment_taxonomy.py`
- `tests/insurance_intelligence/test_mo025_current_baseline_certification.py`

## Scope boundaries

MO-026B does not introduce:

- cross-benefit weights;
- aggregate product score;
- winner selection;
- customer-specific importance;
- suitability reasoning;
- recommendation;
- premium/value judgement.

## Next prerequisite

Before a governed copayment assessment policy is added, close the deferred CD-1 semantic defect concerning `unless` / `except` style exception parsing. Copayment quality depends on preserving percentage, trigger, exception, and scope separately; a malformed exception can materially alter the assessment and therefore must fail closed before MO-026 expands into conditional financial-restriction policies.
