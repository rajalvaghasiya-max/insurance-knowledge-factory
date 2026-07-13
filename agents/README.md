# Agents

`agents/` contains acquisition and discovery-stage automation. Its outputs are evidence artifacts or candidate signals, not automatically trusted insurance facts.

## Responsibilities

| Component | Role | Primary output |
|---|---|---|
| `discovery_agent.py` | Finds insurer website URLs for capture. | URL discovery queue |
| `preservation_agent.py` | Captures website content and preservation metadata. | Raw HTML/text/screenshots + metadata |
| `queue_capture_agent.py` | Runs capture against queued URLs. | Captured source artifacts |
| `html_section_agent.py` | Converts captured HTML into structured sections. | `parsed/html_sections/` records |
| `document_collector_agent.py` | Collects product documents from known/selected links. | Download inputs / document workspace artifacts |
| `pdf_intelligence/pdf_discovery_agent.py` | Discovers PDF URLs and assigns document-type candidates. | `discovery/pdf_queue/` |
| `pdf_intelligence/pdf_download_agent.py` | Downloads PDFs, validates response content, hashes versions, and updates the PDF registry. | `archive/raw_pdf/`, `registry/pdf_registry.json` |
| `product_signal_extractor.py` | Produces page-level candidate product signals from parsed HTML. | `signals/product_signals/` |
| `product_consolidation_agent.py` | Groups eligible product signals into draft Product Master records. | `knowledge_domains/product/product_master/` |
| `knowledge_extractor/extract_product_intelligence.py` | Legacy/product-workspace extractor for documents already placed under a Health product folder. | `knowledge/health/<insurer>/<product>/intelligence/` |
| `knowledge_extractor/extract_policy_intelligence.py` | Extracts selected policy intelligence from product workspace documents. | Product workspace intelligence/validation artifacts |

## Important trust boundaries

```text
Captured webpage/PDF
→ parsed source
→ candidate signal
→ draft consolidated record
→ identity-resolved evidence
→ trusted product fact
```

`ProductSignalExtractor` detects `page_intent`, product-name candidates, UIN-like values, and topic signals. Its output may contain category, FAQ, article, or generic page information. It is not authority for product identity.

`ProductConsolidationAgent` currently accepts signals only where:

```text
page_intent == "individual_product"
AND product_names is non-empty
```

This gate is a safety boundary. It must be tested before modification.

## Current architectural issue

The current `individual_product` detection uses a Python list of known URL keywords. That is a prototype mechanism and must be replaced by governed configuration and evidence-based classification. Product categories must never be registered as products merely because their URLs include insurance-related words.

## Usage

Use runners in `scripts/`, not direct ad hoc invocation, unless debugging a single component.

```powershell
python -m scripts.run_source_discovery
python -m scripts.run_pdf_discovery
python -m scripts.run_pdf_download
python -m scripts.run_html_sectioning
python -m scripts.run_product_signal_extraction
python -m scripts.run_product_consolidation
```

## Agent design rules

- Preserve source provenance in every output.
- Keep raw source capture immutable; create new derived outputs rather than overwriting history.
- Do not encode insurer/product truth in generic Python logic.
- Candidate extraction must not silently become product identity confirmation.
- Fail closed: emit `unknown`, `ambiguous`, or `unresolved` rather than guessing.
