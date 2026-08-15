# AR-2.5.C5 — knowledge_domains Succession Firewall

## Status

Implementation complete; certification pending local test execution.

Audit baseline: `feature/mo-028b-health-waiting-period-coverage`

## Objective

Complete the architectural succession boundary around `knowledge_domains/` without deleting potentially reusable upstream manufacturing capability.

## Decision

`knowledge_domains/` is classified as `TRANSITIONAL_REVIEW_REQUIRED`.

It is not a canonical destination for new PolicyScna architecture.

The current authoritative production packages are:

- `factory_core/`
- `insurance_intelligence/`

Production Python under those packages must not import `knowledge_domains`.

## Preserved capability

AR-2.2 found potentially reusable upstream capability in areas such as evidence routing, deterministic extraction, field registration, validation, document processing, and registry/factory bridges. Those assets remain available for selective migration after explicit review.

This firewall does not declare every module under `knowledge_domains` dead and does not authorize wholesale deletion.

## Superseded / deferred capability

Downstream intelligence paths under `knowledge_domains` remain non-authoritative, including customer-document intelligence, prior publication paths, recommendation-like reasoning, understanding/mental-model layers, financial-outcome simulation, and legacy timeline execution that does not consume current certified knowledge.

## Enforced invariant

```text
factory_core production code
insurance_intelligence production code
        X
        X  must not import
        X
knowledge_domains transitional code
```

This is an import firewall, not a ban on migration. Reusable code may be ported into current contracts with explicit architecture review and new certification.

## Documentation succession

`knowledge_domains/health/README.md` previously stated that Health was the active production domain. That statement is now superseded and the README has been updated to declare the package transitional and to record the AR-2.2 module-level dispositions.

## Certification

Focused certification:

`tests/test_ar25_c5_knowledge_domains_succession_firewall.py`

Required regression after focused pass:

1. `tests/insurance_intelligence`
2. full repository

## Non-goals

This step does not:

- delete `knowledge_domains/`;
- move reusable extraction/manufacturing code;
- redesign factory orchestration;
- change insurance semantics;
- promote any transitional output to governed truth;
- remove historical tests or fixtures.
