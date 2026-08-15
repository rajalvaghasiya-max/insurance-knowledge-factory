# AR-2.5.C3 — First Physical Repository Cleanup

## Audit baseline

Repository: `rajalvaghasiya-max/insurance-knowledge-factory`

Ref: `feature/mo-028b-health-waiting-period-coverage`

## Decision

Remove:

`agents/knowledge_extractor/extract_product_intelligence_v0_2_backup.py.py`

Disposition: **DELETE — HISTORICAL BACKUP / DUPLICATE-EXTENSION ARTIFACT**

## Evidence

The corrected deterministic AR-2.5 cleanup audit identified exactly one remaining candidate. The file was not classified for automatic deletion because two historical MO-007 architecture records referenced it:

- `docs/architecture/MO-007_STAR_COPAY_GENERIC_CAPABILITY_RECONCILIATION.md`
- `docs/architecture/mo_007_star_copay_generic_capability_reconciliation.json`

Those references record a historical audit finding: the backup file contained old-pipeline, product-specific extraction logic and had already been flagged as a repository-hygiene issue. They are evidence that the file existed at the time of MO-007 and should remain unchanged as historical snapshots.

The file itself is a duplicate-extension backup (`.py.py`), belongs to the old `agents/knowledge_extractor` pipeline, and is not an authoritative current component under the AR-2.5 architecture classification.

## Historical-record rule

The MO-007 records are intentionally **not edited** to erase their reference to the removed file. Git history preserves the exact source file reviewed at that milestone. This AR-2.5 record is the later governing disposition for its physical presence in the current tree.

Therefore:

- historical claim that the file was inspected remains true;
- current-tree claim is that the file is removed;
- no current architecture or runtime may depend on it;
- removal does not migrate or endorse any logic contained in the backup.

## Cleanup boundary

This decision does **not** authorize deletion of:

- `knowledge_domains/` wholesale;
- mixed `agents/` acquisition components;
- `factory_sdk/` or `knowledge_factory/` wholesale;
- legacy recommendation scripts retained as bypass/firewall fixtures;
- historical generated artifacts still serving certification/evaluation purposes.

Those remain subject to explicit disposition and dependency review.

## Certification requirement

After deletion, run:

1. `tests/test_ar25_repository_cleanup_audit.py`
2. `scripts/audit_repository_cleanup_candidates.py`
3. `tests/insurance_intelligence`
4. full repository `pytest -q`

Expected cleanup-audit state: **0 candidates**.
