# AFR-N1 — Canonical Ontology Closure Gap Assessment

**Status:** ACTIVE — TRACEABILITY HOLD ONLY  
**Date:** 2026-08-15

## Purpose

This checkpoint follows AFR-N1.A through AFR-N1.E. Its purpose is to compare the implemented behavior against the approved Canonical Insurance Ontology acceptance criteria and the Phase-1 roadmap exit gate before authorizing AFR-N1 closure.

## Certification evidence now validated locally

```text
AFR-N1.A focused                         9 passed
AFR-N1.B focused                         3 passed
AFR-N1.C focused                         6 passed
AFR-N1.D focused                         6 passed
AFR-N1.E focused                         6 passed
HG-3 restoration semantic regression     6 passed
AFR-N1.A through E combined             30 passed
insurance_intelligence                2898 passed
regressions                               0
```

AFR-N1.A through AFR-N1.E are individually certified.

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

This hostile row preserves **two distinct original definition identities**: `No Claim Bonus` and `Cumulative Bonus`. The source itself describes them as “two contradictory entries.”

### 4. Co-payment conditionality

**Required:** canonical meaning must not turn co-payment into a universal fixed percentage; product value/trigger/exception/scope remain product facts.

**Coverage:** AFR-N1.D.  
**State:** SATISFIED.

### 5. Restoration trigger structure + restoration != recharge

**Required:** preserve trigger/use mechanics and encode restoration/recharge as false friends rather than unconditional synonyms.

**Coverage:** AFR-N1.E.  
**State:** SATISFIED and revalidated after the false-synonym repair.

## Governance-contract requirements

The approved design also requires governed standard-definition entries to carry source authority, evidence class, effective range, version, category-scoped identity, reference-never-mutate behavior and fail-closed resolution.

AFR-N1.A establishes and adversarially tests those structural invariants. Subsequent records reuse the same contract.

## Regression-set identity recovery result

A recovery pass was performed across retained project material, uploaded historical artifacts, and repository search.

What is supported:

- the approved Canonical Insurance Ontology artifact explicitly says the **eleven pasted definitions are the regression set**;
- its hostile-case table preserves **six distinct original definition identities**:
  1. Pre-existing Disease;
  2. Room Rent;
  3. No Claim Bonus;
  4. Cumulative Bonus;
  5. Co-payment;
  6. Automatic Restoration;
- the broader MO-024 terminology seed describes a separate 20–30 concept candidate vocabulary and is not evidence of the historical eleven-term membership.

What is **not** supported by the retained material inspected so far:

- the exact identities of the remaining **five** members of the historical eleven-term pasted set.

Therefore the current `health_seed.py` catalogue, the MO-024 candidate list, or other convenient Health concepts must not be used to reconstruct those five by assumption.

An explicit incomplete manifest now records this state:

`docs/architecture/AFR_N1_ELEVEN_TERM_REGRESSION_SET_TRACEABILITY.json`

The manifest contains six source-confirmed identities and five `NOT_RECOVERED` slots. It is intentionally not a substitute for the missing source.

## Remaining closure blocker

AFR-N1 is technically green for every acceptance behavior whose identity is traceable, but full milestone certification remains blocked by one governance issue only:

```text
EXACT ELEVEN-TERM REGRESSION-SET TRACEABILITY
confirmed: 6 / 11
unresolved: 5 / 11
```

This is not evidence of a semantic representation defect and does not justify another ontology abstraction, database migration, knowledge graph, vector-store change or product-specific rule.

## Next authorized action

Locate the original source artifact/conversation that contains the complete eleven pasted definitions. Once recovered:

1. replace the five unresolved manifest slots with exact identities plus provenance;
2. map each recovered identity to existing certified tests where coverage already exists;
3. add only genuinely missing source-backed coverage;
4. run one final manifest-driven AFR-N1 certification suite;
5. close AFR-N1 only if all eleven trace cleanly.

If the original source is no longer recoverable, AFR-N1 must remain held unless the project makes an explicit governed decision to supersede the historical eleven-term exit criterion with a newly defined regression set. That would be a governance decision, not an inference made silently during implementation.

## Architecture conclusion

AFR-N1.A–E demonstrate that the current architecture supports valid-time versioning, source/evidence authority metadata, immutable governed definitions, category isolation, fail-closed alias resolution, false-synonym guards, separation of canonical meaning from product facts, and mechanic-rich product implementations under shared product-neutral concepts.

No ontology rewrite is justified by the evidence so far.
