# Factory SDK v1.2

SDK-1.2 adds the core infrastructure objects that every future PolicyScna production line should use.

## New core modules

```text
factory_sdk/core/factory_asset.py
factory_sdk/core/factory_report.py
factory_sdk/core/factory_certification.py
factory_sdk/core/factory_lineage.py
factory_sdk/core/factory_metadata.py
factory_sdk/quality/determinism_verifier.py
```

## Design intent

This sprint is additive. It does not break the existing `FactoryProductionLine` or the SDK scanner.

The goal is to make the Factory standards explicit in code:

- every asset has common metadata
- every asset has lineage
- every report has a common structure
- every certification has gates
- deterministic fingerprints can ignore known volatile fields

## Next step

After copying these files, run the existing SDK scanner again:

```powershell
python -m scripts.run_knowledge_component_scanner_sdk
```

Then we can start migrating one SDK production line to use `FactoryAsset`, `FactoryReport`, `FactoryCertification`, and `FactoryLineage` directly.
