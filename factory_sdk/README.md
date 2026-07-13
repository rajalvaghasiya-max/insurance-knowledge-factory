# Factory SDK

`factory_sdk/` provides the shared technical contracts used by Factory production lines. It is intentionally domain-neutral.

## What belongs here

| Area | Responsibility |
|---|---|
| `core/` | Factory asset, certification, inspection, lineage, metadata, and report contracts. |
| `golden_concept_pipeline/` | Cross-department GCP orchestration, dependency resolution, production cells, dispatching, queue/state, output collection, and reporting. |
| `quality/` | Determinism verification helpers. |
| `testing/` | Reusable test support. |
| top-level hashing/models/determinism modules | Shared stable identities and deterministic execution support. |

## Core lifecycle contract

A Factory asset has more than content. It must be interpretable by lifecycle state:

```text
trust_basis
runtime_readiness
disposition
lineage/provenance
certification status
```

Typical trust bases include evidence-backed, derived, illustrative, unverified, and invalid-for-use. Do not label illustrative scenario material as a product fact.

## Golden Concept Pipeline

The pipeline coordinates reusable production cells:

```text
package definition
→ dependency resolver
→ manufacturing queue / state
→ department dispatcher
→ production cells
→ output collector
→ certification/report
```

Production cells must advertise the concept scope they support. Unsupported concepts should fail visibly rather than fall through to an unrelated implementation.

## SDK design rules

- Additive changes are preferred over breaking changes.
- Stable IDs and deterministic outputs are first-class requirements.
- Domain-specific extraction should stay out of this layer.
- A declared property is weaker than a verified property; the architecture should move from declaration to verification deliberately.

Historical SDK notes are retained in `README_SDK_1_2.md` and `README_SDK_1_3.md`.
