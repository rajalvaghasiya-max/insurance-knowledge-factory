# AFR-N1.D — Co-payment Definition vs Product Conditionality Gate

**Status:** CERTIFIED  
**Date:** 2026-08-15

## Certification evidence

```text
AFR-N1.D focused copayment tests       6 passed
AFR-N1.A + B + C + D combined         24 passed
insurance_intelligence               2892 passed
regressions                              0
```

## Why this slice exists

A governed ontology must explain what a co-payment *is* without silently asserting that a particular product, policyholder or claim is subject to one.

This is a high-risk boundary because a standard definition and a product rule can contain overlapping words such as `percentage`, `admissible claim amount` and `co-payment`, while serving very different authority roles.

AFR-N1.D pressure-tests that separation using:

1. current IRDAI Health guidance for the generic meaning of co-payment; and
2. the already-certified Star Comprehensive conditional co-payment product binding for product-specific value, trigger, exception and scope.

## Primary-source standard meaning

Current IRDAI Health guidance defines co-payment structurally as a specified amount / percentage of the admissible claim amount to be paid by the policyholder / insured.

The governed standard-definition seed therefore contains:

```text
canonical concept : health.definition.copayment
category          : health
source authority  : IRDAI
source class      : PRIMARY_REGULATOR_GUIDANCE_SOURCE
valid from        : 2024-05-29
```

The standard definition intentionally contains no Star product identity, percentage, age trigger, renewal exception or policy-section scope.

## Product-specific meaning remains elsewhere

The certified Star Comprehensive rule path continues to own the real product mechanics:

```text
value       : 10% of admissible claim amount
trigger     : age at entry 61 years or above
exception   : entered before 61 and renewed continuously without break
scope       : specified Sections II.1 through II.25 subset
```

Those mechanics come from governed product policy wording and the conditional-obligation reasoning path. They are not copied into the ontology definition.

## Architecture invariant

```text
STANDARD DEFINITION
    answers: what does co-payment mean?

PRODUCT BINDING + RULE
    answers: does this product impose one,
             how much,
             when,
             for whom,
             with what exceptions,
             and within what scope?
```

Neither layer may substitute for the other.

## Certified result

AFR-N1.D proves that the standard-definition layer can carry the product-neutral meaning of co-payment while the governed product/rule layer independently carries conditional value, trigger, exception and scope. No Star-specific product mechanics leak into the ontology definition, and no ontology definition is treated as evidence that a product actually imposes a co-payment.

AFR-N1 remains open. The next hostile semantic case is restoration/recharge terminology versus product-specific trigger semantics.
