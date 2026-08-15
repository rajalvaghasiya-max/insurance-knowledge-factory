# PHASE-2A — First Multi-Insurer Health Batch

**Status:** SELECTED  
**Date:** 2026-08-15

## Purpose

This batch is the first operational test of Phase-2A data-only Health scaling after certification of the initial MO-029 review-risk routing increment.

It is not a plan-specific implementation milestone.

The batch exists to measure whether the existing generic onboarding and review contracts can operate across multiple insurers while preserving:

```text
normal new Health product onboarding
=
0 product-identity-bearing production code
```

## Selected batch

### 1. Star Health — Star Comprehensive

Role in batch:

- hostile commercial-product fixture already used to pressure conditional copayment, waiting periods, delivery/newborn limits and restoration mechanics;
- strong governed evidence lineage;
- useful high-complexity reference for review-risk distribution and residue handling.

No new Star-specific production reasoning is authorized.

### 2. Bajaj General Insurance — My Health Care Plan

Role in batch:

- recently certified through generic registration, version transition, currentness review and publication-eligibility gates;
- useful control case for a product whose current immutable version is governed without Bajaj-specific runtime logic;
- provides a clean baseline for onboarding-step and review-workload measurement.

No new Bajaj-specific production reasoning is authorized.

### 3. Aditya Birla Health — Activ One NXT

Role in batch:

- historical product-specific Super Reload implementation already exists and is retained only as an audit/compatibility fixture;
- useful for determining which behavior/evidence is already representable through generic governed artifacts and where historical product-specific code still acts as a dependency;
- useful for exposing succession/fencing work without treating `activ_one_nxt.py` as the scaling template.

No expansion of Activ One-specific production code is authorized.

## Batch acceptance rules

For each product measure at minimum:

- source documents available and registered;
- document identity/currentness state;
- evidence/review-group count where applicable;
- MO-029 risk-tier distribution;
- human decisions required;
- material residue;
- fail-closed events;
- governed spec/data files added or changed;
- production-code files changed;
- product-identity-bearing production-code changes.

The desired production-code result is:

```text
product-identity-bearing production-code changes = 0
```

If normal onboarding requires a new product-specific Python module, conditional branch, hard-coded product identifier or mechanic implementation, the batch records an architecture/scaling defect and stops that path.

## Important interpretation

This three-product set is a **process-scaling batch**, not sufficient evidence by itself that the factory scales across the full Health market.

Two products have substantial historical architecture pressure behind them and Activ One NXT contains historical product-specific production code. Therefore this batch is used first to:

1. operationalize common measurements;
2. identify remaining product-specific dependencies;
3. exercise MO-029 workload routing;
4. prepare the path for subsequent genuinely new products to enter as governed data only.

The next batch must expand beyond these historical fixtures once the common measurement/onboarding harness is stable.

## Immediate execution sequence

1. Build one generic batch-audit/measurement contract that reads governed artifacts and produces per-product onboarding/review metrics.
2. Do not encode the three product identities in production branching; product entries belong in a batch specification.
3. Run the audit across the three selected fixtures.
4. Record unsupported/missing artifacts explicitly rather than manufacturing them.
5. Use the resulting friction map to decide the smallest generic Phase-2A improvement before adding further Health products.

## Exit criterion for this batch

```text
one generic batch spec
+ one generic measurement/audit path
+ 3 insurers evaluated
+ MO-029 risk metrics captured where review groups exist
+ missing/unavailable metrics explicit
+ product-specific production-code additions = 0
+ no silent residue
+ relevant regressions = 0
```
