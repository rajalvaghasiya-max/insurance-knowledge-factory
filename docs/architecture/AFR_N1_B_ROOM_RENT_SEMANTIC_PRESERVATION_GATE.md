# AFR-N1.B — Room Rent Semantic-Preservation Gate

**Status:** IMPLEMENTED — VALIDATION PENDING  
**Date:** 2026-08-15

## Pressure being tested

AFR-N1.B tests whether the governed standard-definition layer preserves the full semantic content of a standardized insurance definition instead of collapsing it into a convenient label/value pair.

The pressure unit is **Room Rent**.

The IRDAI Master Circular on Standardization of Health Insurance Products (Ref. `IRDAI/HLT/REG/CIR/193/07/2020`) defines Room Rent in a way that includes both:

- room and boarding expenses; and
- associated medical expenses.

Losing the second element is not harmless compression. It changes the economic meaning a downstream explainer may give to a room-rent restriction.

## Authority boundary

The 2020 IRDAI circular is pinned as the primary regulatory source for the historical governed definition.

AFR-N1.B deliberately **does not** claim that this record remains the current regulatory definition after the 2024 framework transition. The current IRDAI Health framework has been identified, but the exact primary-source room-rent definition has not yet been pinned strongly enough to justify carrying the 2020 record forward indefinitely.

Therefore:

- historical lookup within the governed validity window resolves the IRDAI definition;
- current lookup fails closed until a current primary source is pinned;
- insurer product wording may corroborate or locate terminology but is not promoted to regulatory authority.

## Implementation

`insurance_intelligence/terminology/health_regulatory_definition_seed.py` now contains the historical Room Rent governed definition:

```text
canonical concept : health.definition.room_rent
category          : health
source            : IRDAI/HLT/REG/CIR/193/07/2020
effective_from    : 2020-10-01
effective_to      : 2024-03-31
```

No new ontology abstraction was required. The AFR-N1.A valid-time contract is sufficient.

## Adversarial certification tests

`tests/insurance_intelligence/test_afr_n1b_room_rent_semantic_preservation.py` proves:

1. historical Room Rent resolution preserves `Room and Boarding expenses`;
2. it also preserves `associated medical expenses`;
3. the concept cannot be simplified to room charge only;
4. the record remains primary-regulatory-source governed;
5. a current lookup fails closed while current primary-source authority is unresolved.

## Exit criterion

```text
AFR-N1.B focused room-rent tests       GREEN
AFR-N1.A + AFR-N1.B combined           GREEN
insurance_intelligence                 GREEN
regressions                                0
```

AFR-N1.B is a semantic-preservation pressure gate, not permission to infer product-specific room-rent limits, proportional deductions, eligibility, or claim outcomes. Those remain product-fact/applicability concerns.
