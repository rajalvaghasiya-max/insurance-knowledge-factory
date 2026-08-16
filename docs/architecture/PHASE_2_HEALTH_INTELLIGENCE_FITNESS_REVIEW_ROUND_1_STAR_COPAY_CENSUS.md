# Phase 2 — Health Intelligence Fitness Review — Round 1C Star Conditional Copay Census

**Status:** WITHHELD — SEMANTIC RULE REVIEWED; LINEAGE FIELD DEFECT FOUND  
**Date:** 2026-08-16

## Question under review

`Q-COPAY-01` — Does the Star Comprehensive conditional copay apply, and what does it mean?

Product:

```text
Star Health — Star Comprehensive Insurance Policy
current governed policy-wording content SHA-256:
b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f
```

This is a material-harm question. Candidate Green status therefore requires a census check.

## Question-shape split

General-shaped proposition:

> What is the conditional copayment rule?

Instance-shaped proposition:

> Will this copayment apply to me / this claim?

The latter cannot be Green without resolving the customer/policy/claim variables.

Manual question-shape correction log:

```text
existing runtime misclassification observed = NO EVIDENCE ESTABLISHED IN THIS CHECK
manual reviewer classification performed    = YES
architecture pressure                        = NO
```

## Reviewed semantic proposition

The governed binding records the reviewed statement that Star Comprehensive applies:

- 10% co-payment;
- to each and every claim within the stated covered sections;
- for fresh as well as renewal policies where insured person's age at entry is 61 years or above;
- with an exception where the insured person entered before attaining 61 and renewed continuously without a break;
- limited to the enumerated Sections II.1–II.11, II.15 and II.25 as recorded in the governed binding.

The production certification path preserves obligation value, trigger, exception, applicability scope and calculation basis separately.

## Current-source identity

The generic source registration records:

```text
document_version_id = docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75
content_sha256       = b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f
```

The governed legal-condition binding records the evidence candidate as:

```text
candidate_id          = candidate_page_39
candidate_text_sha256 = ea3aa9a64bd799fbdcc52bdebb48a5b6917c90673451cf84230005506bb09594
document_version_id   = docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75
source_page           = 39
```

Therefore `ea3aa9...` is a **candidate-text hash**, not the policy-wording source-artifact hash.

## Lineage defect found

The production certification module currently defines:

```text
STAR_COMPREHENSIVE_COPAYMENT_EVIDENCE_HASH = ea3aa9...
```

and writes that value into:

```text
Lineage.source_artifact_sha256
Lineage.governed_record_sha256
```

This is semantically mislabeled:

- `source_artifact_sha256` should identify the current source artifact (`b1dbe8...`), not the candidate text fragment;
- `governed_record_sha256` should identify the governed binding record bytes, not the candidate text fragment.

The current tests reinforce the existing mislabeled behavior by asserting that all evidence packages carry `ea3aa9...` as `source_artifact_sha256`.

## Fitness Review consequence

The semantic rule itself is not disproved by this finding. The reviewed statement remains tied to page 39 of the `b1dbe8...` document version through the governed binding.

However the Fitness Review may not certify the answer `ANSWERABLE_VERIFIED` while the production lineage contract reports the candidate-text hash as the source-artifact hash.

Therefore:

```text
general semantic proposition   = SOURCE-SUPPORTED
production lineage integrity   = FAIL / MISLABELED
answerability_status            = ANSWERABLE_PENDING_SPOTCHECK
blocker_class                   = CURRENTNESS_OR_LINEAGE_UNVERIFIED
work_type                       = GOVERNANCE_CORRECTION
architecture_pressure           = NO
```

No product/insurance semantic abstraction is missing.

## Instance-variable guard

Even after lineage repair, the question:

> Will this copay apply to me?

requires at least:

- insured person's age at entry;
- whether entry occurred before age 61;
- whether renewal has been continuous without a break;
- whether the claim falls in one of the enumerated covered sections;
- any additional customer/policy context required to identify the applicable rule instance.

Unresolved load-bearing variables cap the customer-specific answer at `ANSWERABLE_WITH_LIMITATIONS` or `BLOCKED`.

## Customer-safe communication

### What is known

The reviewed current Star Comprehensive wording contains a 10% conditional copayment rule based on age at entry, with a continuous-renewal exception and enumerated section scope.

### What is unresolved for a customer instance

The customer's age-at-entry, continuous-renewal history and claim-section applicability have not been supplied/resolved in this review.

### Customer-safe message

> The plan has a 10% conditional co-payment rule tied to age at entry, but whether it applies to you depends on when you entered the policy, whether you have renewed continuously without a break, and which policy section your claim falls under. I need those details before I can safely say the co-payment applies to your claim.

### What would unblock

1. repair/verify the production lineage fields against the current governed document and binding record; and
2. for an instance answer, resolve age-at-entry, continuity and claim-section context.

## Falsification outcome

Insurance-semantic representation:

```text
FOUND_AND_REPRESENTABLE
```

Governance lineage:

```text
FOUND_DEFECT — candidate-text SHA is mislabeled as source-artifact/governed-record SHA
```

This does not justify a new insurance reasoning architecture gate. It requires a bounded governance correction after the no-runtime-code review phase authorizes implementation.

## Interaction-assumption sensor

No restoration/capacity, deductible, room-rent or payment-order assumption is required to state the conditional copay trigger/exception itself.

The phrase `admissible claim amount` may become material for a future monetary ordering/payment question, but this census check does not infer what mechanics precede calculation of that amount.

If later source review seeks to answer copay-versus-capacity precedence, `admissible claim amount` must be treated as a potential scope/ordering term and may yield `FOUND_BUT_AMBIGUOUS_SCOPE` unless current wording resolves the relationship explicitly.

## Review conclusion

The Fitness Review correctly refuses to promote the Star copay cell to Green despite a previously passing certification suite. The semantic proposition appears sound, but the production lineage fields conflate candidate-text hash with source-artifact and governed-record hashes.

This is a governance/trustworthiness finding — exactly the class of defect the Fitness Review was designed to surface before relying on the answer for a real customer.
