# Scripts and Runbooks

`scripts/` provides explicit CLI entry points. Prefer these runners over importing internal classes from an interactive shell: runners standardize paths, logs, output locations, and summary reporting.

## Source acquisition and parsing

| Runner | Purpose |
|---|---|
| `run_discovery.py` / `run_source_discovery.py` | Discover insurer website URLs. |
| `run_queue_capture.py` | Capture queued website URLs. |
| `run_html_sectioning.py` | Build structured HTML section artifacts. |
| `run_pdf_discovery.py` | Discover document links and populate PDF queues. |
| `run_pdf_download.py` | Download and version PDFs. |
| `discover_product_documents_live.py` / `discover_product_documents_browser.py` | Product-specific document discovery helpers. |
| `download_product_documents.py` / `parse_product_documents.py` | Legacy/product-workspace document acquisition and parsing. |

## Product discovery and audit

| Runner | Purpose |
|---|---|
| `run_product_signal_extraction.py` | Create candidate signals from parsed website sections. |
| `run_product_consolidation.py` | Consolidate eligible signals into draft Product Master records. |
| `audit_product_identity.py` | Audit product identity readiness and UIN-related conditions. |
| `audit_product_coverage.py` / `audit_portfolio_coverage.py` | Audit coverage of products/fields across the portfolio. |
| `validate_product_intelligence.py` / `validate_extraction.py` | Validate legacy/product-workspace intelligence outputs. |

## Health field extraction and evidence routing

| Runner | Purpose |
|---|---|
| `run_evidence_router.py` | Produce evidence routing plans for a product field. |
| `run_copay_extraction.py` | Run Copay extraction. |
| `run_room_rent_extraction.py` | Run room-rent extraction. |
| `run_first_health_fact_extraction.py` | Legacy/initial field-extraction workflow. |

## Factory manufacturing lines

| Runner | Purpose |
|---|---|
| `run_document_processing_engine.py` | Process a controlled document into Factory components. |
| `run_knowledge_component_scanner.py` / `_sdk.py` | Scan components and produce observations. |
| `run_knowledge_component_normalizer.py` | Normalize and consolidate component artifacts. |
| `run_knowledge_component_classifier.py` | Classify normalized components. |
| `run_knowledge_manufacturing_engine.py` | Manufacture knowledge blocks/topics. |
| `run_knowledge_distillation_engine.py` | Distil observations and relationships. |
| `run_mental_model_transformation_line.py` | Build mental-model transformations. |
| `run_financial_outcome_simulation.py` | Run financial-outcome scenario simulation. |
| `run_understanding_asset_manufacturing_line.py` | Manufacture understanding assets. |
| `run_learning_primitive_manufacturing_line.py` | Manufacture learning primitives. |
| `run_learning_path_manufacturing_line.py` | Manufacture learning paths. |
| `run_advisor_intelligence_asset.py` | Build advisor-intelligence assets. |
| `run_decision_intelligence_asset.py` | Build decision-intelligence assets. |

## Golden Concept and governance validation

| Runner | Purpose |
|---|---|
| `run_golden_concept_package.py` | Build/evaluate a Golden Concept Package. |
| `run_golden_concept_pipeline.py` | Execute the cross-department Golden Concept pipeline. |
| `run_gmvs.py` | Run the Generic Manufacturing Validation System. |
| `run_gmvs_waiting_period_validation.py` | Run the Waiting Period GMVS validation scenario. |
| `run_factory_manager.py` | Run the Health Factory manager/status orchestration. |

## Safe operating sequence

For a newly discovered website source:

```text
source discovery
→ capture
→ sectioning
→ source/page classification
→ product signal extraction
→ identity resolution
→ product consolidation (only eligible assets)
→ evidence routing / field extraction
```

For Golden Concept work, do not bypass certification or GMVS just to produce a visible asset.

## Testing before and after changes

```powershell
pytest
pytest tests/health -ra
pytest tests/gmvs -ra
```

Run targeted tests during iteration, then run the complete suite before a commit.
