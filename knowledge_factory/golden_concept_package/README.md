# PolicyScna — Insurance Knowledge Factory

> **Mission:** Increase understanding by continuously manufacturing trusted insurance intelligence.

PolicyScna is not a chatbot, CRM, comparison website, or consumer app. It is an evidence-led factory that turns insurer and regulatory source material into traceable knowledge, understanding assets, mental models, financial outcomes, and decision-support assets.

## Operating principles

- **Evidence before explanation.** No product assertion should outrun its source evidence.
- **Deterministic before AI inference.** Rules, validators, and provenance decide trust; AI may assist later within constrained boundaries.
- **Unknown over invented.** Missing, conflicting, or ambiguous evidence remains visible as unresolved.
- **Immutable provenance.** Raw source artifacts and their capture history are retained; derived outputs identify their inputs.
- **Reusable capability before one-off implementation.** Do not hardcode insurer/product facts in Factory core.

The detailed governance record lives in `knowledge_factory/governance/`.

## Architecture at a glance

```text
Discover / capture sources
        ↓
archive + parsed source artifacts + registries
        ↓
source asset classification and scope routing
        ↓
product identity resolution (UIN-first where applicable)
        ↓
evidence routing and field extraction
        ↓
knowledge manufacturing
        ↓
understanding, mental-model, and financial-outcome assets
        ↓
advisor / decision intelligence
        ↓
Golden Concept Package certification and GMVS
```

## Repository map

| Path | Purpose |
|---|---|
| `agents/` | Capture, discovery, PDF acquisition, sectioning, product signals, and product consolidation. |
| `scripts/` | Explicit command-line runners for pipeline steps and audits. |
| `archive/` | Raw captured HTML, text, screenshots, and PDFs. Do not treat filenames as business identity. |
| `parsed/` | Parsed website sections, keyed by source content. |
| `discovery/` | URL and PDF discovery queues. |
| `registry/` | Technical/source registries, including insurer, source, semantic, PDF, and trap registries. |
| `signals/` | Discovery-stage product signal outputs. These are not trusted product facts. |
| `knowledge/` | Generated output artifacts, product workspaces, Golden Concept packages, and reports. |
| `knowledge_domains/` | Domain-specific manufacturing logic. Health is the active production domain. |
| `knowledge_factory/` | Cross-domain factory architecture: governance, GCP, GMVS, advisor, and decision intelligence. |
| `factory_sdk/` | Shared asset, lineage, certification, determinism, and production-line contracts. |
| `tests/` | Canonical automated test suite. |

## Trust boundaries

```text
Raw source / captured artifact
→ source evidence
→ candidate signal
→ resolved identity / validated field fact
→ certified manufactured asset
```

Do not collapse these states. A UIN found on a generic page is a **candidate occurrence**, not proof that the page belongs to that product. A Product Master record is currently a discovery/consolidation output and must not automatically become trusted product identity.

## Current production focus

**Health** is the active domain. Established capabilities include evidence routing, core Health field extraction, Copay Golden Concept manufacturing, Waiting Period timeline capability, governance, and GMVS baseline testing.

### Immediate milestone: P1.5a.0 — Product Signal Safety Contract

1. Add test coverage for source/page classification and consolidation eligibility.
2. Retain `page_intent` as a low-level signal, and add a derived `asset_scope`.
3. Route only `asset_scope = product_specific` into product consolidation.
4. Remove product/category URL keyword lists from Python and place approved patterns in governed configuration.
5. Rebuild Product Master; current records remain provisional.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install
pytest
```

`pytest.ini` defines `tests/` as the canonical test root.

## Important commands

```powershell
# Full test suite
pytest

# Discover source URLs
python -m scripts.run_discovery

# Extract website product signals
python -m scripts.run_product_signal_extraction

# Build draft Product Master records
python -m scripts.run_product_consolidation

# Run the Factory manager
python -m scripts.run_factory_manager

# Run GMVS
python -m scripts.run_gmvs
```

See `scripts/README.md` for the runner catalogue and `tests/README.md` for testing rules.

## What this repository is not building now

- Advisor CRM or lead management
- Consumer/mobile frontend
- Generic chatbot
- Claims workflow application
- Premature scale infrastructure

Interfaces are downstream of trusted intelligence.
