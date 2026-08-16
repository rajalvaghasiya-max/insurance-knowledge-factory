# Phase 2 — Activ One Real Cross-Insurer Restoration Portability Gate

**Status:** CERTIFIED AND FROZEN  
**Date:** 2026-08-16

## Purpose

Test whether the generic restoration state evaluator certified in the Bajaj stateful-mechanic gate can execute a second insurer's materially different current-governed restoration rule without evaluator modification, product-specific production reasoning, or reuse of stale product facts.

This gate is the required real-insurer follow-up to the prior Bajaj + synthetic-conformance proof. The successful result establishes real cross-insurer restoration evaluator portability for the bounded rule shapes exercised here. It does not establish arbitrary stateful-composition or claims-adjudication capability.

## Primary pressure case

```text
Aditya Birla Health — Activ One
UIN: ADIHLIP24097V012324
current governed policy-wording SHA-256:
38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16
```

Only the current immutable `38bb...` source establishes product facts in this gate.

## Historical-artifact safeguard

The repository contains a historical Activ One NXT `Super Reload` product implementation anchored to missing policy-wording SHA:

```text
d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451
```

That historical implementation remains non-current factual authority. It was used only as a search locator and representation-pressure reference.

No historical asserted mechanic was accepted as current truth unless independently re-derived from `38bb...`.

## Current-source qualification

Current `38bb...` wording under `C.10 Super Reload` independently establishes:

```text
activation trigger = Base Sum Insured + accumulated Super Credit (if applicable)
                     completely exhausted OR insufficient for covering a claim
reload amount      = Base Sum Insured
frequency          = unlimited times during Policy Year
covered sections   = C.1 Hospitalization Treatment / C.5 Domiciliary Hospitalization /
                     C.6 Home Health Care / C.7 AYUSH Treatment / C.8 Organ Donor Expenses
first-claim rule   = Super Reload not payable to first claim in life of Policy where so specified
                     in Policy Schedule/Product Benefit Table
single-claim max   = Base Sum Insured
Super Credit calc  = Super Reload does not increase accumulated Super Credit calculation base
```

Current Product Benefit Table wording additionally states:

```text
Super Reload = From 2nd claim of Policy Life - Unlimited times
```

The current source also explicitly preserves the utilization sequence:

```text
Base Sum Insured
-> Super Credit (if inbuilt / opted and applicable)
-> Super Reload
-> Cancer Booster (if opted and applicable)
```

That sequence is repeated under `C.13.10 Cancer Booster`, providing current-source corroboration.

## Material difference from Bajaj

The certified Bajaj rule shape is bounded to reinstatement use on a subsequent claim, normally after discharge/gap conditions.

Current Activ One is materially different:

```text
Bajaj      = subsequent-claim-only restoration consumption
Activ One  = Super Reload may participate when Base SI + Super Credit are exhausted
             or insufficient for the current claim, subject to first-claim and other governed rules
```

Therefore the second insurer is not merely a value variation; it pressures a different claim-sequence/effective-point shape.

## Current qualification artifact

Current-source facts are materialized at:

```text
knowledge/factory/registry_backed/aditya_birla_health_activ_one/governance/super_reload_current_source_qualification.json
```

Historical `d772...` facts remain quarantined.

## Portability execution proof

The frozen generic evaluator:

```text
insurance_intelligence/benefits/restoration_state.py
```

was not modified to support current Activ One.

A current Activ One rule parameterization was executed through the same evaluator already used for Bajaj. The test exercises same-triggering-claim participation and contrasts it with the Bajaj subsequent-claim-only shape.

Focused portability command:

```text
python -m pytest -q \
  tests/insurance_intelligence/test_restoration_state_evaluator.py \
  tests/insurance_intelligence/test_activ_one_current_restoration_portability.py
```

Result:

```text
12 passed
```

No insurer/product identity branch or product-specific evaluator modification was introduced.

## Cross-insurer claim now earned

The prior restoration gate proved:

```text
Bajaj current rule + materially different synthetic rule
-> one generic evaluator
```

This gate now proves:

```text
Bajaj current governed restoration rule
+
Activ One current governed Super Reload rule
-> same generic evaluator
-> no product-specific evaluator change
```

Therefore **real cross-insurer restoration evaluator generalization is certified for the bounded rule shapes exercised by these two current-governed products**.

This claim is intentionally narrower than arbitrary restoration semantics or claims adjudication.

## Composition / ordering finding

Current Activ One wording creates genuine interaction pressure through the explicit sequence:

```text
Base SI -> Super Credit -> Super Reload -> Cancer Booster
```

This is consequential because availability of one capacity depends on the exhaustion/insufficiency state of preceding capacities.

The portability gate records this as **current governed composition evidence**, but it does not build or certify a general multi-mechanic claim-composition engine.

That is a separate future pressure case.

## ASSERTED / DERIVED discipline

Current Activ One facts are ASSERTED only when independently supported by `38bb...`.

Any evaluator-produced outputs remain DERIVED and must retain their asserted input/evaluator lineage. Historical `d772...` evidence is not accepted as a current evidence reference.

## Explicit non-claims

This gate does not prove:

- arbitrary stateful interaction handling;
- generic ordering across all benefit mechanics;
- copay/deductible ordering;
- complete Super Credit computation;
- Cancer Booster adjudication;
- arbitrary restoration shapes outside the bounded Bajaj/Activ One semantics exercised;
- whole-product governed readiness;
- individual claim payment/admissibility.

## Pass conditions

1. Current-source integrity — PASS.
2. Historical stale facts quarantined unless reverified — PASS.
3. Materially different current restoration semantics execute through same evaluator — PASS.
4. Counterfactual claim-state execution — PASS.
5. Current ordering semantics preserved without scalar collapse — PASS as representation/evidence; full composition evaluation remains out of scope.
6. No unresolved or stale fact promoted through publication — PASS for this portability gate; no new whole-product publication claim made.
7. No whole-product readiness or arbitrary adjudication inference — PASS.

## Regression evidence

Focused portability suite:

```text
12 passed
```

No evaluator modification was required after the prior frozen Bajaj restoration gate.

## Final architecture conclusion

The restoration architecture has now progressed through three evidence levels:

```text
1. single-insurer stateful rule execution
2. synthetic materially-different rule-shape portability
3. real second-insurer current-governed portability
```

The third level is now proven.

The next unresolved architectural pressure revealed by current Health evidence is not restoration portability. It is **composition/ordering of multiple capacity mechanics**, especially the current Activ One sequence:

```text
Base SI -> Super Credit -> Super Reload -> Cancer Booster
```

This gate is frozen. Do not extend it into a composition engine or further restoration tuning.
