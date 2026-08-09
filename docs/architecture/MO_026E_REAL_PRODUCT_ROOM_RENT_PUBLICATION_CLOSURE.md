# MO-026E — Real-Product Room-Rent Publication Closure

Status: **CLOSED — SOURCE-LIMITED REAL-PRODUCT PUBLICATION CERTIFIED**

## Objective

Establish an authoritative active-path publication boundary for a real product's room-rent fact without consuming historical `knowledge_domains` extraction outputs or silently inventing unresolved policy mechanics.

## Certified product

- Insurer: Aditya Birla Health Insurance
- Product: Activ One
- Variant: Activ One NXT
- UIN: `ADIHLIP24097V012324`

## Certified result

The governed publication preserves the official insurer product-page statement that Activ One NXT has no capping on room rent / ICU and associated listed medical expenses up to the Base Sum Insured.

The publication deliberately records the source as an official insurer product page rather than policy wording.

The product page's exposed policy-wording link was found to resolve to a different product/UIN and is therefore rejected for Activ One NXT governance.

## Governance boundary

Only an exact `GovernedRoomRentFactPublication` that is approved and published may project into the active `GovernedRoomRentRestriction` assessment contract.

Historical extractor outputs, mappings, and arbitrary objects remain inadmissible.

The projection preserves:

- insurer/product/variant identity;
- exact product UIN;
- governed claim text;
- evidence reference identity;
- source authority type;
- bounded evidence hash;
- publication/review status;
- source limitations.

## Fail-closed result

The no-room-rent-cap fact is preserved, but proportionate-deduction applicability is not explicitly governed by the accepted source.

Therefore:

- `cap_type = NO_LIMIT`
- `proportionate_deduction = UNKNOWN`
- MO-026 room-rent assessment result = `NOT_SCORABLE`

PolicyScna does **not** turn the favorable no-cap fact into a `VERY_STRONG` assessment while a material interaction mechanic remains unresolved.

## Certification evidence

Focused MO-026A–E certification completed with:

**74 passed**

The suite covered:

- exact product/UIN preservation;
- source-limited publication semantics;
- rejection of arbitrary/unpublished publication inputs;
- bounded evidence identity;
- propagation of source limitations into assessment;
- real-product fail-closed assessment while proportionate deduction remains unresolved;
- no overall score, rank, winner, weighting, suitability, or recommendation surface.

## Deferred completion condition

Full real-product room-rent assessment remains blocked until correct Activ One NXT policy wording or an equivalent authoritative governed source establishes the proportionate-deduction mechanic.

This is a deliberate governance block, not an implementation defect.

## Architectural conclusion

MO-026E proves that PolicyScna can publish a favorable real-product fact while still refusing to overstate the product when a material claim-time interaction remains unresolved.

This behavior is consistent with the product principle:

> Evidence before explanation. Unknown over invented.
