# AFR-N1.E — Restoration vs Recharge / Trigger-Semantics Gate

**Status:** IMPLEMENTED — VALIDATION PENDING  
**Date:** 2026-08-15

## Why this slice exists

Insurance products use overlapping marketing terms such as restoration, recharge, reload and super reload. A canonical ontology may route those phrases to one broad benefit family, but it must not infer that the underlying mechanics are interchangeable.

AFR-N1.E pressure-tests that boundary using two already-governed Health implementations:

- Star Comprehensive — `Automatic Restoration of Sum Insured`
- Aditya Birla Activ One NXT — `Super Reload`

Both map to the same governed restoration concept. Their mechanics are materially different.

## Architecture decision

No new `recharge` benefit concept is introduced merely because an insurer uses alternate marketing language.

The existing terminology layer may treat `recharge benefit` as a routing alias for the restoration topic. The governed benefit layer remains responsible for the actual product behavior through explicit mechanic dimensions.

The generic restoration concept already requires product-specific dimensions including:

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

Therefore neither a common ontology concept nor similar marketing language may be used to manufacture shared product behavior.

## Invariant

```text
USER / INSURER PHRASE
    restoration / recharge / reload / super reload
                ↓
        TERMINOLOGY ROUTING
                ↓
    governed restoration concept
                ↓
      PRODUCT IMPLEMENTATION
                ↓
 explicit trigger + timing + frequency + use mechanics
```

Routing convergence is permitted. Mechanic convergence must be proven by product evidence, never assumed.

## Adversarial tests

`tests/insurance_intelligence/test_afr_n1e_restoration_recharge_trigger_semantics.py`

proves:

1. `recharge benefit` is a routing alias, not a separate governed benefit merely because of wording;
2. the product-neutral restoration concept requires explicit trigger/use dimensions;
3. Star preserves its once-after-exhaustion/subsequent-hospitalization mechanics;
4. Activ One NXT Super Reload preserves its unlimited/insufficient-capacity/same-claim mechanics;
5. both implementations share a concept while retaining different behavior signatures;
6. shared ontology identity does not imply identical entitlement or claim behavior.

## Exit criterion

```text
AFR-N1.E focused restoration/recharge tests   GREEN
AFR-N1.A through E combined                   GREEN
insurance_intelligence                        GREEN
regressions                                       0
```

No production abstraction change is authorized unless these tests reveal a real representation gap. Current inspection indicates the existing terminology + benefit-contract split is sufficient.
