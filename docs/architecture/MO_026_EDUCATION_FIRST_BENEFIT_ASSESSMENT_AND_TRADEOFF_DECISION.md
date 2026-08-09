# MO-026 — Education-First Benefit Assessment and Trade-off Decision

## Status

APPROVED ARCHITECTURE DECISION

## Purpose

PolicyScna exists to educate users about insurance so that they can make informed decisions. It should not decide on the user's behalf by default.

This record supersedes the earlier framing of MO-026 as an "Explainable Ranking Engine".

The authoritative milestone name is now:

**MO-026 — Explainable Insurance Benefit Assessment & Trade-off Engine**

The following milestone remains separate:

**MO-027 — Customer Suitability & Decision Support**

## Governing principle

PolicyScna explains products by default. It recommends only when the user explicitly asks for decision support and sufficient relevant customer context is available.

MO-026 must therefore answer:

- What is strong about each plan?
- What is restrictive about each plan?
- How do governed benefit mechanics differ?
- What are the practical implications of those differences?
- Which policy mechanics interact with or constrain other benefits?
- What material protection warnings should not be hidden?
- What remains unknown or not safely scorable?

MO-026 must not answer by default:

- Which product is objectively best?
- Which product should this customer buy?
- Which insurer is the winner?
- What is the user's personalized utility function?

## Authoritative output

The primary MO-026 artifact is not a product score or ranking.

The primary artifact is a governed product benefit profile and cross-product trade-off analysis.

Conceptually:

```text
GovernedProductBenefitProfile

Product identity
Benefit assessments
Protection-floor alerts
Strength tags
Restriction tags
Interaction warnings
Unknown / not-scorable dimensions
Evidence coverage
Optional quote context
```

A cross-product analysis should produce:

```text
Plan A stronger on:
- ...

Plan B stronger on:
- ...

Material restrictions in Plan A:
- ...

Material restrictions in Plan B:
- ...

Important trade-offs:
- ...

Interactions that affect practical meaning:
- ...

Unknown / unresolved items:
- ...
```

No overall winner is required.

## Benefit-level judgment remains governed

Removing a composite score does not remove judgment.

A benefit-level classification such as STRONG or RESTRICTIVE is still an analytical conclusion and must be evidence-backed and versioned.

Each assessment must preserve at least:

```text
dimension_id
source governed value(s)
assessment classification
assessment policy/version
reason
source evidence references
limitations
status/confidence
interaction warnings
```

Preferred user-facing classifications are semantic rather than false-precision numeric scores:

- VERY_STRONG
- STRONG
- MODERATE
- RESTRICTIVE
- VERY_RESTRICTIVE
- NOT_SCORABLE

Internal normalized values may exist later for derived lenses, but must not replace the governed semantic assessment.

## Decision-role taxonomy

Each assessment dimension must declare its decision role.

Initial taxonomy:

- PROTECTION_FLOOR
- CORE_PROTECTION
- PREFERENCE
- CONTEXT_DEPENDENT
- PRICE

Examples:

### PROTECTION_FLOOR

Material restrictions that must remain visible regardless of user preference, subject to governed applicability:

- high compulsory or materially restrictive copayment
- room-rent-linked proportionate deduction
- major disease/procedure sub-limits
- other claim-wide financial restrictions

These warnings are non-suppressible by optional weighting or user preference.

### CORE_PROTECTION

Material policy mechanics that substantially affect usable protection but are not necessarily universal hard floors:

- restoration mechanics
- waiting periods
- consumables/non-medical-expense coverage
- coverage-section limitations
- cumulative bonus mechanics

### PREFERENCE / CONTEXT_DEPENDENT

Features whose importance legitimately depends on customer needs or circumstances:

- AYUSH preference
- maternity relevance
- geographic/network preference
- optional add-ons

### PRICE

Premium is quote-specific and must remain separate from static product-quality assessment.

## Interaction-aware assessment

Per-benefit cards must not imply that insurance mechanics are independent.

MO-026 must support governed interaction warnings.

Example:

```text
Room-rent restriction
    -> may activate proportionate deduction
    -> may reduce admissible hospitalization expenses
    -> may reduce the practical value realized from sum insured or restoration
```

Another example:

```text
Restoration
    -> depends on trigger requirement
    -> depends on same-hospitalization use
    -> depends on covered-section scope
```

An interaction rule must describe relationships, not invent claim outcomes.

The intended contract shape is approximately:

```text
InteractionRule
source_dimension_id
target_dimension_id
interaction_type
condition
severity
explanation
```

MO-026 does not estimate a future claim payout merely because an interaction exists.

## Financial restriction family

Copayment, room-rent restrictions, proportionate deduction, deductibles, sub-limits, and sum-insured mechanics must not be treated as independent scalar features when they act on the same claim economics.

MO-026 should preserve a structured claim-financial-exposure profile rather than collapsing these mechanics prematurely into one additive score.

The system may classify structural restriction severity, but must not present a predicted realized claim payment without sufficient claim-specific facts and a separately governed capability.

## Copayment requirement

Copayment is not a scalar percentage.

The assessment must preserve, where supported:

- percentage
- trigger
- exception
- applicability scope
- evidence

This makes correct exception semantics a prerequisite for trustworthy ranking/assessment expansion.

The existing deferred CD-1 issue (`unless` / `except` style exception semantics) remains open and must be closed or fail-closed before broad MO-026 certification over conditional rule families.

## Missingness

Missing information must never become zero, average, or silently inferred.

Use NOT_SCORABLE where the governed evidence is insufficient.

Cross-product comparison must use a common comparable universe rather than independently renormalizing each product over different known dimensions.

The output must expose:

- comparable dimensions
- excluded dimensions
- unresolved dimensions
- coverage / completeness status

Any future threshold for whether an overall derived lens may run must be an explicit governed policy.

## Premium and quote context

Premium is not a static product fact.

Premium may be included only through a quote-specific governed snapshot with sufficient comparability context.

The product profile must keep PRICE separate from policy-quality classifications.

The quote layer should preserve at least:

```text
quote_id
insurer_id
product_id
product_variant_id
customer_context_id
member composition
location
sum insured
policy tenure
deductible
selected add-ons
premium before tax
tax treatment
final premium
quote date
validity/source evidence
```

Price-enabled analysis should initially be described as **price-adjusted analysis**, not "value-for-money", unless a separately governed protection-per-rupee model exists.

## Optional derived ranking

An overall weighted ranking is not the primary MO-026 artifact and is not required for milestone success.

If a user explicitly asks for an overall rating/ranking, the system must not silently apply a universal "typical customer" weight vector.

The preferred route is:

1. explain the benefit-by-benefit profile;
2. ask the minimum relevant questions needed to understand the user's priorities;
3. preserve those answers as explicit decision context;
4. apply an explicitly selected or user-derived weighting lens;
5. keep protection-floor warnings visible outside that weighting;
6. explain why the derived result changes with those priorities.

If this workflow becomes personalized enough to decide which product fits the specific customer, it crosses into MO-027.

## MO-026 / MO-027 boundary

### MO-026 — Explainable Insurance Benefit Assessment & Trade-off Engine

Product-centric.

Default behavior:

- educate;
- compare benefit mechanics;
- highlight strengths;
- highlight restrictions;
- explain implications;
- surface interactions;
- preserve material warnings;
- expose unknowns;
- leave the decision with the user.

### MO-027 — Customer Suitability & Decision Support

Customer-context-centric.

May consume:

- MO-026 governed product/trade-off analysis;
- explicit user priorities;
- age/family/location where relevant;
- health context where relevant and appropriately handled;
- budget constraints;
- existing coverage;
- other material decision context.

MO-027 may then say:

> Based on the priorities and circumstances you provided, Plan A appears more suitable because ...

It must not say that a plan is universally best.

Any recommendation must be traceable to:

```text
product evidence
+
governed benefit/trade-off analysis
+
explicit customer context/priorities
```

## Milestone decomposition

The current implementation plan is:

- MO-026A — Benefit Assessment Contracts and Dimension Taxonomy
- MO-026B — Governed Dimension Assessment Policies
- MO-026C — Protection-Floor Classification
- MO-026D — Benefit Interaction Registry
- MO-026E — Governed Product Benefit Profile
- MO-026F — Cross-Product Benefit Profile Comparison
- MO-026G — Strength / Restriction / Trade-off Summary Projection
- MO-026H — Optional User-Selected Weighting Lens
- MO-026I — Optional Derived Explainable Ranking
- MO-026J — Quote/Price-Adjusted Analysis Boundary

MO-026E through MO-026G are the primary milestone value.

MO-026H through MO-026J are optional derived lenses and must not redefine the authoritative product assessment artifact.

## Success criterion

MO-026 is successful when PolicyScna can deterministically assess and compare insurance products benefit-by-benefit, explain strengths and restrictions in simple language, surface material interactions and protection warnings, preserve evidence and unknowns, and help a user understand the trade-offs without making the purchase decision on the user's behalf.
