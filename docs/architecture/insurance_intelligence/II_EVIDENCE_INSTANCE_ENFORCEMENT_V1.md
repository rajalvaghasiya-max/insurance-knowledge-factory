# Insurance Intelligence — Evidence Instance Enforcement v1

## Status

Bounded hardening slice between Instance Sufficiency and MO-016 Evidence Resolution.

## Decision

MO-016 Evidence Resolver remains unchanged. Its authority, version, lineage, repository and deterministic sufficiency behavior are reused as-is.

The hardening required is a preflight invariant:

> Instance-sensitive evidence resolution may not use the Evidence Resolver as a substitute for governed instance sufficiency.

The new `EvidenceInstanceEnforcer` requires the request's `InstanceSufficiencyOutput` to be `PASS` with `planning_authorized=true` before delegating to the existing resolver.

If Instance Sufficiency is `CLARIFICATION_REQUIRED`, `NOT_ANSWERABLE`, or `OUT_OF_SCOPE`, Evidence Resolution is not called.

## Why

The original MO-016 pilot resolver can resolve a planner `subject_reference` against governed aliases/identities. That remains useful as downstream verification, but after introduction of the Instance Sufficiency Guard it must not become an alternate path that bypasses the earlier identity attestation boundary.

This wrapper makes the ordering invariant executable without rewriting MO-016.

## Non-goals

This slice does not:

- change evidence authority precedence;
- change currentness or version rules;
- change lineage checks;
- change evidence sufficiency aggregation;
- introduce semantic identity matching;
- authorize advisory or recommendation execution;
- modify Knowledge Factory identity governance;
- modify Reasoning or Decision/Safety behavior.

## Executable invariant

```text
Context
  ↓
Instance Sufficiency
  ↓ PASS only
Reasoning Plan
  ↓
EvidenceInstanceEnforcer
  ↓ PASS only
existing MO-016 Evidence Resolver
```

A non-PASS instance result must leave the underlying resolver call count at zero.
