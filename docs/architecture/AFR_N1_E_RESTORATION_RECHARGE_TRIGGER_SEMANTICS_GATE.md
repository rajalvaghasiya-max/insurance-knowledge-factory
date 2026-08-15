# AFR-N1.E — Restoration vs Recharge / Trigger-Semantics Gate

**Status:** REVALIDATION PENDING AFTER ACCEPTANCE-CRITERION REPAIR  
**Date:** 2026-08-15

## Why this slice exists

Insurance products use overlapping marketing terms such as restoration, recharge, reload and super reload. Similar wording must not cause PolicyScna to collapse materially different mechanics into one product behavior.

AFR-N1.E pressure-tests that boundary using two already-governed Health implementations:

- Star Comprehensive — `Automatic Restoration of Sum Insured`
- Aditya Birla Activ One NXT — `Super Reload`

Both map to the same governed restoration benefit concept. Their mechanics are materially different.

## Acceptance-criterion correction discovered during review

The first N1.E implementation treated `recharge benefit` as a routing alias. Its six focused tests and the insurance-intelligence subsystem were green (`6 / 30 / 2898`).

The subsequent AFR-N1 gap assessment compared that implementation against the approved Canonical Insurance Ontology acceptance criterion and found a mismatch: the approved design explicitly requires `restoration ≠ recharge` to be preserved as a false-synonym guard rather than silently normalized as an alias.

Therefore the green mechanics result is retained as evidence, but N1.E is not certified until the corrected false-synonym behavior is revalidated.

## Architecture decision

No new `recharge` benefit concept is introduced merely because an insurer uses alternate marketing language. But `recharge`, `recharge benefit`, `refill`, `refill benefit`, and `reinstatement` are no longer exact aliases of the canonical restoration terminology concept.

The canonical terminology contract now supports explicit `not_synonyms`. A false-synonym phrase is not entered into the exact phrase index and therefore cannot silently resolve to restoration.

This does **not** prevent a governed product implementation such as Activ One NXT `Super Reload` from referencing the generic restoration benefit concept. That mapping is product-governed and mechanic-rich; it is not inferred merely from the word `reload`.

The governed benefit layer remains responsible for actual product behavior through explicit mechanic dimensions including:

- restoration percentage;
- restoration count per policy period;
- trigger requirement;
- trigger timing;
- same-hospitalization use;
- subsequent-hospitalization use;
- same-illness use;
- policy-year behavior and related optional mechanics.

## Real hostile comparison

### Star Comprehensive

```text
marketing name        : Automatic Restoration of Sum Insured
restoration           : 100%
count                  : once per policy period
trigger                : exhaustion of basic SI + accrued cumulative bonus, if any
trigger timing         : immediately upon exhaustion
same hospitalization   : no
subsequent admission   : yes
same illness           : yes
```

### Activ One NXT

```text
marketing name        : Super Reload
restoration           : 100% per activation
count                  : unlimited during policy year
trigger                : exhausted OR insufficient available capacity
trigger timing         : within the admissible claim when capacity is insufficient
same hospitalization   : yes
subsequent admission   : yes
```

Therefore neither a common ontology concept nor similar marketing language may manufacture shared product behavior.

## Corrected invariant

```text
EXACT CANONICAL TERMINOLOGY
    "restoration benefit"
            ↓
    restoration topic

FALSE-FRIEND TERMINOLOGY
    "recharge benefit" / "refill" / "reinstatement"
            ↓
    no exact canonical resolution
            ↓
    clarification / governed product mapping required

GOVERNED PRODUCT IMPLEMENTATION
    e.g. Super Reload
            ↓
    restoration concept only when product evidence establishes the mapping
            ↓
    explicit trigger + timing + frequency + use mechanics
```

## Adversarial tests

`tests/insurance_intelligence/test_afr_n1e_restoration_recharge_trigger_semantics.py`

now proves:

1. `recharge benefit` is an explicit false synonym and does not exact-resolve as restoration;
2. the product-neutral restoration concept requires explicit trigger/use dimensions;
3. Star preserves its once-after-exhaustion/subsequent-hospitalization mechanics;
4. Activ One NXT Super Reload preserves its unlimited/insufficient-capacity/same-claim mechanics;
5. both implementations share a governed benefit concept while retaining different behavior signatures;
6. shared benefit-concept identity does not imply identical entitlement or claim behavior.

The older HG-3 restoration regression has also been updated so the repository no longer contains a conflicting assertion that `recharge benefit` must be a restoration alias.

## Exit criterion

```text
AFR-N1.E focused restoration/recharge tests   GREEN
HG-3 restoration semantic regression          GREEN
AFR-N1.A through E combined                   GREEN
insurance_intelligence                        GREEN
regressions                                       0
```

No new product-specific reasoning code is authorized by this repair. The change is confined to the canonical terminology boundary and its tests.
