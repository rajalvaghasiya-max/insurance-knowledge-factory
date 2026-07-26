# PolicyScna Factory SDK v1.3 — Factory Core

SDK-1.3 adds the **Factory Inspector**, the first governance layer for production-line outputs.

## What changed

New file:

```text
factory_sdk/core/factory_inspector.py
```

Updated exports:

```text
factory_sdk/core/__init__.py
factory_sdk/__init__.py
```

## New core objects

```python
FactoryInspector
FactoryInspectionResult
InspectionIssue
```

## Purpose

The Factory Inspector checks whether a production-line run respects the Factory contract:

- asset type matches contract
- department boundary is preserved
- determinism is declared or verified
- asset identity exists
- traceability exists
- report contract exists
- certification passed
- event contract exists
- quality threshold is met

## Important design decision

SDK-1.3 is additive. It should not break the existing SDK scanner.

Today the scanner may still show:

```text
deterministic_declared
```

Future SDK versions should move toward:

```text
deterministic_verified
```

## Example

```python
from factory_sdk import FactoryInspector

inspection = FactoryInspector().inspect_run(
    contract=contract.to_dict(),
    asset=asset_dict,
    report=report_dict,
    certification=certification_dict,
    event=event_dict,
)

print(inspection.to_dict())
```

## Sprint status

SDK-1.3 establishes Factory governance without forcing existing production lines to change immediately.
