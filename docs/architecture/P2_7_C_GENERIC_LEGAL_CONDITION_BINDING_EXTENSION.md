# P2.7-C — Generic Legal Condition Binding Extension

## Purpose
Extend the certified generic legal condition binding contract to support a reviewed, evidence-bound conditional co-payment rule discovered in the first cross-insurer replication pilot.

## Change
Add `conditional_copayment_rule` to the allowed assertion types.

## Unchanged safety controls
- The assertion must be human-reviewed.
- All evidence selections must reference registered reusable-generic sources.
- Exactly one evidence selection must have `primary_legal` authority.
- Candidate text hashes are checked before binding.
- Discovery-only sources remain blocked.
- Private, policy-instance, group-specific and member-specific sources remain blocked by the registration/classification model.
- Room/ICU entitlement semantic keys remain blocked.
- Output remains `bound_not_published`.

## Why this is a capability extension, not a product exception
The new assertion type describes a reusable insurance mechanism: a co-payment whose applicability depends on stated conditions. It does not contain Star Health, product, age, percentage, or policy-section logic in Factory code. Those details remain in the reviewed binding specification and evidence spans.

## Regression intent
Existing P2.5 room-rent assertion types remain allowed without changes. New tests prove the co-payment rule is accepted only with the same primary-source and evidence-integrity requirements.
