# AFR-N1 — Canonical Ontology Closure Gap Assessment

**Status:** ACTIVE — CLOSURE NOT YET AUTHORIZED  
**Date:** 2026-08-15

## Purpose

This checkpoint follows AFR-N1.A through AFR-N1.E. Its purpose is to stop one-off gate creation long enough to compare the implemented behavior against the approved Canonical Insurance Ontology acceptance criteria and the Phase-1 roadmap exit gate.

## Evidence already validated locally

Before the N1.E acceptance-criterion repair, local validation reported:

```text
AFR-N1.A focused                         9 passed
AFR-N1.B focused                         3 passed
AFR-N1.C focused                         6 passed
AFR-N1.D focused                         6 passed
AFR-N1.E mechanics pressure              6 passed
AFR-N1.A through E combined             30 passed
insurance_intelligence                2898 passed
regressions                               0
```

A through D are certified. N1.E mechanics were green, but N1.E certification is intentionally withheld until the false-synonym repair is revalidated.

## Approved acceptance behavior vs current implementation

The retained Canonical Insurance Ontology design states that the original eleven pasted definitions form the regression set and explicitly calls out five consequential hostile cases.

### 1. PED stale four-year meaning

**Required:** reject/correct the stale four-year meaning and resolve the governed 36-month definition by valid time.

**Coverage:** AFR-N1.A.

**State:** SATISFIED.

### 2. Room Rent semantic coupling

**Required:** preserve the `associated medical expenses` consequence rather than collapsing Room Rent to room charge only.

**Coverage:** AFR-N1.B.

**State:** SATISFIED for the governed historical definition window; current lookup deliberately fails closed where current primary-source authority is not pinned.

### 3. Motor NCB vs Health Cumulative Bonus

**Required:** category namespaces must prevent semantic merger.

**Coverage:** AFR-N1.C.

**State:** SATISFIED.

### 4. Co-payment conditionality

**Required:** canonical meaning must not turn co-payment into a universal fixed percentage; product value/trigger/exception/scope remain product facts.

**Coverage:** AFR-N1.D.

**State:** SATISFIED.

### 5. Restoration trigger structure + restoration != recharge

**Required:** preserve trigger/use mechanics and encode restoration/recharge as false friends rather than unconditional synonyms.

**Coverage:** AFR-N1.E.

**State:** MECHANICS SATISFIED; FALSE-SYNONYM REPAIR IMPLEMENTED; REVALIDATION PENDING.

The gap assessment found that the earlier terminology seed still treated `recharge benefit` as an exact restoration alias even though the approved ontology design explicitly requires a `not_synonyms` guard. The repair adds `not_synonyms` to the canonical terminology contract, removes recharge/refill/reinstatement from exact restoration routing, and updates the affected regressions.

## Governance-contract requirements

The approved design also requires every governed standard-definition entry to carry:

- source authority;
- evidence class;
- effective range;
- version;
- category-scoped identity;
- reference-never-mutate behavior;
- fail-closed resolution.

AFR-N1.A establishes and adversarially tests those structural invariants. Subsequent definition records reuse the same contract.

## The remaining closure blocker

The roadmap says the **eleven pasted definitions** are the Phase-1 canonical-ontology regression set. The retained architecture artifact available in the repository/project material explicitly enumerates the five hostile errors above, but it does **not enumerate the identities of all eleven original pasted terms**.

Therefore AFR-N1 must not be declared fully certified merely because the five hostile cases are green.

This is a traceability gap, not evidence that six new ontology abstractions are required.

### What we must not do

- Do not guess the missing six terms from the current `health_seed.py` contents.
- Do not manufacture a new eleven-term set after the fact.
- Do not treat current terminology catalogue size as proof of the historical regression-set identity.
- Do not close AFR-N1 until the original eleven-term identity is pinned to an authoritative project artifact or reconstructed from the original source material with explicit provenance.

## Immediate next validation

First revalidate the N1.E repair:

```text
AFR-N1.E focused                         GREEN
HG-3 restoration semantic regression     GREEN
AFR-N1.A through E combined              GREEN
insurance_intelligence                   GREEN
regressions                                  0
```

If green, certify N1.E.

Then perform a **regression-set identity recovery**, not another semantic gate:

1. locate the original eleven pasted definitions in retained project material/history;
2. record the exact eleven term identities in a governed regression-set manifest;
3. map each term to an existing certified gate/test where coverage already exists;
4. add only the missing tests/source-backed records actually required by that manifest;
5. run one final AFR-N1 certification suite against the manifest.

## Architecture conclusion

The A–E work has already demonstrated that the current architecture can support:

- valid-time definition versioning;
- source/evidence authority metadata;
- immutable governed definitions;
- category isolation;
- exact alias resolution with fail-closed behavior;
- explicit false-synonym guards;
- separation of ontology meaning from product facts;
- mechanic-rich product implementations under a shared product-neutral concept.

No ontology rewrite is justified by the evidence so far.

AFR-N1 closure is currently blocked by **(a) N1.E repair revalidation and (b) exact eleven-term regression-set traceability**, not by a proven need for a new database, knowledge graph, vector store, or product-specific reasoning layer.
