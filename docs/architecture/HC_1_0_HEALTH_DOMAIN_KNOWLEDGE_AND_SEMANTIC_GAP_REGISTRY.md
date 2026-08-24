# HC-1.0 — Health Domain Knowledge & Semantic Gap Registry

Status: FROZEN FOR IMPLEMENTATION
Date: 2026-08-24

## Purpose

HC-1 catalogs Health insurance vocabulary broadly while keeping typed product semantics evidence-earned. The registry is a gap ledger, not a completion dashboard.

## Core distinction

Products are efficient at discovering semantic variants but inefficient at discovering vocabulary. Therefore:

- vocabulary, authoritative definitions, boundaries, synonyms, and important questions may be catalogued proactively;
- typed semantic contracts may be added only when real authoritative evidence demonstrates the need and the existing representation is insufficient.

## Claim-aspect placement rule

Concepts are not globally assigned to one plane. Each governed claim-aspect is assigned to the plane whose authority/version/applicability model governs that claim.

Planes:

1. `RegulatoryLifecycle` — effective-dated regulatory rights, definitions, floors, continuity rules, supersession.
2. `ProductMechanic` — per-product-version benefit, exclusion, cost-sharing, limit, eligibility, and implementation mechanics.
3. `ClaimsOperational` — claims process, network/TPA/cashless/reimbursement/preauthorization/documentation mechanics.

A concept may have aspects in more than one plane and those aspects cross-reference rather than collapse into one global record.

Examples:

- PED regulatory definition → RegulatoryLifecycle.
- PED waiting-period implementation for product X → ProductMechanic.
- Portability right/timeline → RegulatoryLifecycle.
- Product X treatment of ported continuity → ProductMechanic.

## DomainKnowledge maturity

DomainKnowledge is concept-level/general-domain maturity only:

- `DK0_UNCATALOGUED`
- `DK1_AUTHORITATIVE_DEFINITION_AVAILABLE`
- `DK2_CONCEPT_BOUNDARY_DEFINED`
- `DK3_EXPLANATION_READY`

### Hard instance guard

DomainKnowledge maturity MUST NOT satisfy an instance-specific query when a PolicyInstance, policy Schedule, customer document, or other resolved instance context is in scope.

An instance-specific query MUST route to applicable ProductSemantic/ClaimsOperational state and evidence or fail closed. `DK3_EXPLANATION_READY` means only that a general explanation is governed; it never authorizes a product/customer-specific answer.

## ProductSemantic maturity

ProductSemantic is scored at concept + semantic variant + product + product version grain:

- `PS0_UNOBSERVED`
- `PS1_EVIDENCE_OBSERVED`
- `PS2_REPRESENTABLE`
- `PS3_EVIDENCE_BINDABLE`
- `PS4_CERTIFIED`
- `PS5_REASONING_VALIDATED`

Blocking states are not maturity scores:

- `REPRESENTATION_GAP`
- `KNOWLEDGE_GAP`
- `CONFLICT`
- `CURRENTNESS_UNRESOLVED`
- `POLICY_CONTEXT_REQUIRED`

## Variant-grain truth rule

A concept MUST NOT be represented as globally complete/certified/green when any known semantic variant remains blocked or unsupported.

Example:

`waiting_period` may contain certified variants for INITIAL, PRE_EXISTING_DISEASE, SPECIFIC_DISEASE_PROCEDURE and still retain `personal_underwriting_specific = REPRESENTATION_GAP`.

## Unknown variant space invariant

Every concept permanently carries `unknown_variant_space_open = true`.

Known gaps are never interpreted as the total gap set. The registry MUST NOT expose an aggregate gap-completeness percentage or a claim that the variant space has been exhaustively enumerated.

`KNOWN_GAPS` is a ledger of observed unsupported shapes; `UNKNOWN_VARIANT_SPACE` is a permanent open-world acknowledgement and cannot be closed by registry population.

## Contextual authority rule

Authority is claim-scoped, not globally ranked. Source role is evaluated against claim-aspect, date/version, and instance context.

Examples:

- current regulatory moratorium rule → current IRDAI regulatory authority;
- what room category this customer bought → applicable Policy Schedule/instance evidence;
- what the product contract says generally → current applicable policy wording/CIS/benefit table according to claim type.

## Anti-false-completeness rules

The registry MUST NOT:

- calculate or publish a synthetic Health-domain completion percentage;
- treat definition readiness as product-semantic readiness;
- treat a known-gap count as the total possible gap set;
- infer absence from missing evidence;
- use glossary/domain maturity to answer an instance-specific claim;
- author new typed semantic contracts without evidence-earned pressure;
- hide product-specific decision logic in registry data/config.

## HC-1 worked examples

Initial seeds must include mature and blocked realities:

- copayment;
- waiting_period;
- room_rent / proportionate deduction;
- ReAssure 3.0 personal/underwriting-specific waiting-period REPRESENTATION_GAP;
- ReAssure 3.0 additive/cumulative copayment REPRESENTATION_GAP;
- ReAssure 3.0 multispan room-category copayment certification REPRESENTATION_GAP.

## Niva extension dependency decision

The actual ReAssure 3.0 evidence shows additive/cumulative copayment is independently evidenced on single pages:

- page 44: prolonged-hospitalization trigger + `additional cumulative co-payment of 10%` + final admissible amount basis;
- page 45: non-network transplant/intimation/biopsy trigger + `additional co-payment of 20%` + admissible claim amount basis.

Therefore additive/cumulative copayment semantics do NOT depend on multispan certification for this product.

The multispan dependency is specific to room-category copayment:

- page 6 supplies the trigger/effect linkage: choosing a room outside plan category causes Annexure V copayment to apply on the entire claim;
- page 62 supplies the variant × room-category percentage matrix.

Execution order may remain:

1. HC-1.1 personal/underwriting-specific waiting-period semantics;
2. HC-1.2 additive/cumulative copayment semantics;
3. HC-1.3 multispan copayment certification/component evidence.

This ordering is evidence-specific and does not establish that additive composition can never require multispan evidence on another product.

## Historical experiment integrity

Historical cold-start classifications remain immutable under the rubric version in force when observed.

- Tata product #4 waiting-period remains `CONFIG_SPEC` under v1 even if the later v2 definition would classify the same behavior as REUSE.
- Niva product #5 remains `REPEATABILITY_NOT_PROVEN` with both target concepts recorded as `REPRESENTATION_GAP` before corrective extensions.

Later architecture clarification or successful post-gap validation MUST NOT retroactively re-grade those historical records.
