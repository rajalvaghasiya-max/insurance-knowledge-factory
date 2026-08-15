# AFR-N1.D — Co-payment Definition vs Product Conditionality Gate

**Status:** IMPLEMENTED — VALIDATION PENDING  
**Date:** 2026-08-15

## Why this slice exists

A governed ontology must explain what a co-payment *is* without silently asserting that a particular product, policyholder or claim is subject to one.

This is a high-risk boundary because a standard definition and a product rule can contain overlapping words such as `percentage`, `admissible claim amount` and `co-payment`, while serving very different authority roles.

AFR-N1.D pressure-tests that separation using:

1. current IRDAI Health guidance for the generic meaning of co-payment; and
2. the already-certified Star Comprehensive conditional co-payment product binding for product-specific value, trigger, exception and scope.

## Primary-source standard meaning

Current IRDAI Health guidance defines co-payment structurally as a specified amount / percentage of the admissible claim amount to be paid by the policyholder / insured.

The governed standard-definition seed therefore adds:

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

## Adversarial tests

`tests/insurance_intelligence/test_afr_n1d_copayment_definition_product_conditionality.py`

proves:

1. the current definition preserves the generic cost-sharing structure;
2. co-payment aliases resolve only in the explicit Health category;
3. the standard definition does not contain Star-specific 10%, age, renewal or section terms;
4. the certified Star product binding supplies value, trigger, exception and scope;
5. definition and product binding are complementary rather than interchangeable;
6. the standard-definition contract contains no product/applicability/claim-outcome fields.

## Exit criterion

```text
AFR-N1.D focused copayment tests       GREEN
AFR-N1.A + B + C + D combined         GREEN
insurance_intelligence                 GREEN
regressions                                0
```

AFR-N1 remains open after this gate. The next hostile semantic case is restoration versus recharge/trigger semantics; no product-specific reasoning code is authorized by this ontology gate.
