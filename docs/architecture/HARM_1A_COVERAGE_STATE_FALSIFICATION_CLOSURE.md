# HARM-1A — Coverage-State Falsification Closure

Status: **CLOSED PENDING MERGE**

## Purpose

HARM-1A tested whether PolicyScna's existing generic semantics can preserve six
customer-distinct outcomes without flattening them into one generic
`NOT_COVERED` state:

1. covered now;
2. not covered yet because a waiting condition is active;
3. excluded by the current policy wording;
4. covered only if explicit conditions are satisfied;
5. dependent on the policy instance or Policy Schedule; and
6. not yet determinable from governed evidence.

The test did not pre-authorize a new enum, classifier, evaluator, factory,
validator, or runtime refactor. Success did not require six top-level states;
it required the existing semantic composition to preserve why the answers
differ and to permit a safe response.

## Pre-registered falsification rule

Architecture pressure would be confirmed only if waiting-period restriction,
current-wording exclusion, and conditional coverage reduced to the same
effective semantic state without preserving the reason for the difference.

That falsification trigger was **not met**.

## Evidence-backed results

| Customer-distinct outcome | Current evidence | Classification | Safe disposition |
|---|---|---|---|
| Covered now | Activ One in-patient treatment is documented, but the source also says benefit applicability may depend on the Policy Schedule | `FOUND_BUT_AMBIGUOUS_SCOPE` | Describe the documented benefit with limitations; do not confirm a specific claim |
| Not covered yet | Activ One D.1.2 excludes specified diseases/procedures until 24 months, with explicit accident and continuity qualifications | `FOUND_AND_REPRESENTABLE` | Preserve temporary duration, exception, scope, and timeline status |
| Excluded by current wording | Activ One D.1.4 excludes admissions primarily for diagnostics/evaluation and unrelated diagnostic expenses | `FOUND_AND_REPRESENTABLE` | Preserve an `EXCLUSION_EFFECT`; do not express it as a waiting period |
| Covered only if | Activ One D.1.6 makes obesity-surgery treatment conditional on documented requirements and any applicable waiting period | `FOUND_AND_REPRESENTABLE` | Preserve condition, applicability scope, and conditional status |
| Policy/Schedule dependent | Activ One D.2.8 excludes treatment outside India unless the Policy Schedule provides cover | `INSTANCE_OR_SCHEDULE_CONTEXT_REQUIRED` | Require the schedule and fail closed without it |
| Cannot determine yet | The approved waiting-period evidence profile explicitly withholds the base D.1.3 activation boundary from automation | `CURRENT_SOURCE_MANUFACTURING_GAP` | Return insufficient evidence; govern the exact clause before automation |

The machine-readable scenario record is
`docs/architecture/HARM_1A_COVERAGE_STATE_FALSIFICATION_SPEC.json`.

## Existing semantic composition

The repository already preserves the required distinctions through composition:

- reasoning finding types distinguish `COVERAGE_EFFECT`, `COVERAGE_CONDITION`,
  `EXCLUSION_EFFECT`, and `UNRESOLVED_IMPLICATION`;
- finding status and derivation distinguish supported, limited, conditional,
  and assumption-dependent conclusions;
- condition, trigger, exception, scope, and applicability scope remain separate;
- evidence applicability includes date/variant unresolved and
  `POLICY_SPECIFIC_OVERRIDE` states;
- conflict handling includes `REQUIRES_POLICY_SCHEDULE`;
- deterministic reasoning can block on evidence or approved context;
- response contracts distinguish answers with limitations, clarification, and
  insufficient evidence; and
- the waiting-period timeline model preserves `NOT_ACTIVE` versus `ACTIVE` and
  explicitly refuses to equate timeline completion with claim approval.

No single enum is required to retain the six user-distinct meanings.

## Runtime and manufacturing boundary

The architecture is representationally sufficient, but current governed
manufacturing is incomplete:

- the deterministic Insurance Intelligence rule registry currently provides a
  generic documented-fact rule and conditional-copayment rules, not governed
  exclusion or general coverage-applicability rules;
- the approved waiting-period timeline profile contains one fully specified
  optional-reduction example and explicitly blocks the base initial,
  specified-disease, and PED activation boundaries pending exact source
  isolation; and
- product-level benefit presence must not be promoted into claim-specific
  coverage without instance, schedule, waiting-period, exclusion, and claim
  context.

Those are manufacturing and applicability pressures. They are not proof of a
new runtime architecture requirement.

## Closure decision

`FOUND_AND_NOT_REPRESENTABLE = 0`.

HARM-1A is closed with:

- representation pressure: **not proven**;
- manufacturing pressure: **confirmed**;
- new runtime architecture: **not authorized**; and
- claim-approval or claim-payment guarantee: **not introduced**.

The next isolated milestone is the current-source shape inspection for Star
Comprehensive restoration. Manufacturing remains prohibited until that shape
is established.
