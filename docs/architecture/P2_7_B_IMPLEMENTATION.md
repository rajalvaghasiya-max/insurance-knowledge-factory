# P2.7-B — Star Comprehensive Conditional Co-payment Evidence Binding

## Purpose
Bind one reviewed, reusable, generic legal condition using the existing generic legal-condition binding contract. This is a cross-insurer replication of the already-certified P2.5-H1 path.

## Scope
- Insurer: Star Health and Allied Insurance Company Limited
- Product: Star Comprehensive Insurance Policy
- UIN: SHAHLIP26044V092526
- Primary source: Policy wording, `POL / COMP / V.24 / 2025`
- Corroborating source: Prospectus, `PROS / COMP / V.15 / 2025`
- Concept: conditional co-payment

## Bound rule
A 10% co-payment applies to each claim for insured persons whose entry age is 61 or above, subject to the policy-stated continuous-renewal exception and listed-section scope.

## Explicit non-goals
- Does not calculate a specific claim payable amount.
- Does not infer a co-payment for any omitted section.
- Does not create a product-level "copay applies" simplification.
- Does not publish authoritative knowledge.
- Does not modify the registered sources, classification manifest, legacy intelligence JSON, or any Aditya artifacts.

## Evidence selections
- Policy wording: `candidate_page_39`, SHA-256 `ea3aa9a64bd799fbdcc52bdebb48a5b6917c90673451cf84230005506bb09594`
- Prospectus: `candidate_page_38`, SHA-256 `5bc6f0c81cfcb80ee4aee324ca71b6c280b3c684f04a3a39bcdb042db588c42f`

The source PDFs display a few unrelated header remnants in the extracted stream. Binding relies only on the specified page-level spans that explicitly identify Star Comprehensive and UIN `SHAHLIP26044V092526`.

## Expected result
`reviewed_generic_legal_conditions_bound_not_published` with `assertion_count: 1`.
