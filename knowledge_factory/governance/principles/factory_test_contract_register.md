# Factory Test Contract Register

## Purpose

This register defines the canonical test ownership, verification scope, and allowed claims for PolicyScna production assets.

All executable automated tests must live under the top-level `tests/` directory.

A passing test proves only the behaviour explicitly covered by its contract. It does not automatically prove that an asset is evidence-backed, product-specific, complete, or suitable for customer-facing use.

---

## Test Classification


| Test Type   | Purpose                                                                             |
| ----------- | ----------------------------------------------------------------------------------- |
| Unit        | Verifies one module, model, validator, or deterministic rule in isolation.          |
| Contract    | Verifies a production asset’s required input, output, status, and provenance shape. |
| Integration | Verifies that multiple production components work together correctly.               |
| Regression  | Prevents a previously fixed defect from returning.                                  |
| Governance  | Verifies Factory certification, maturity, readiness, or status truthfulness.        |


---

## Canonical Test Ownership


| Production Area                    | Canonical Test Location                                              | Primary Test Types            | Allowed Claims                                                                                                         |
| ---------------------------------- | -------------------------------------------------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Evidence Router                    | `tests/test_evidence_router.py`                                      | Unit, Contract                | Evidence routing follows configured matching, source-priority, and rejection rules.                                    |
| Product Identity                   | `tests/test_audit_product_identity.py`                               | Contract                      | Product identity checks detect expected identifiers and quality conditions.                                            |
| Product Coverage Audit             | `tests/test_audit_product_coverage.py`                               | Contract                      | Coverage audit reports follow the current audit contract.                                                              |
| Portfolio Coverage Audit           | `tests/test_audit_portfolio_coverage.py`                             | Contract                      | Portfolio-level coverage metrics follow the current audit contract.                                                    |
| Product Intelligence Extraction    | `tests/test_extract_product_intelligence.py`                         | Integration                   | Extraction pipeline produces expected structured output from approved fixtures.                                        |
| Product Intelligence Validation    | `tests/test_validate_product_intelligence.py`                        | Contract, Regression          | Validation rules identify supported, incomplete, and invalid product intelligence.                                     |
| Recommendation Logic               | `tests/test_recommend_products.py`                                   | Unit, Regression              | Recommendation logic follows configured rules; it does not prove suitability without evidence-backed inputs.           |
| Department 04 Scanner              | `tests/department_04/test_knowledge_component_scanner.py`            | Unit, Contract                | Scanner manufactures raw structural components without insurance semantic interpretation.                              |
| Department 04 Normalizer           | `tests/department_04/test_knowledge_component_normalizer.py`         | Unit, Contract, Regression    | Normalizer preserves provenance, classifies structural noise, merges valid continuations, and creates adjacency links. |
| Department 05 Learning Primitives  | `tests/department_05/test_learning_primitive_manufacturing_line.py`  | Unit, Contract                | Learning primitives follow their declared manufacturing contract.                                                      |
| Department 05 Understanding Assets | `tests/department_05/test_understanding_asset_manufacturing_line.py` | Integration, Contract         | Understanding assets are manufactured from supported learning primitives.                                              |
| Copay Understanding Asset          | `tests/understanding/test_copay_understanding_asset.py`              | Regression                    | Copay understanding output remains structurally and semantically consistent with its approved model.                   |
| Knowledge Distillation             | `tests/knowledge_distillation/test_kde_v1.py`                        | Unit, Contract                | Distillation reports preserve required observations and manufacturing opportunities.                                   |
| Mental Model Transformation        | `tests/mental_model_transformation/`                                 | Unit, Integration             | MMTC produces supported concept assets and skips unsupported concepts safely.                                          |
| Financial Outcome Simulation       | `tests/financial_outcome/test_fosc_v1.py`                            | Unit, Contract                | Copay financial illustrations follow deterministic arithmetic and declared limitations.                                |
| Waiting Period Timeline            | `tests/waiting_period_timeline/`                                     | Unit, Integration, Regression | Timeline logic evaluates approved rules with runtime dates; it does not determine final claim approval.                |
| Advisor Intelligence               | `tests/advisor_intelligence/`                                        | Unit, Contract                | Advisor assets follow their declared manufacturing and certification contracts.                                        |
| Decision Intelligence              | `tests/decision_intelligence/`                                       | Unit, Contract                | Decision assets follow their declared manufacturing and certification contracts.                                       |
| Golden Concept Package             | `tests/golden_concept_package/`                                      | Contract                      | Package assembly follows the Golden Concept Package contract.                                                          |
| Golden Concept Pipeline            | `tests/golden_concept_pipeline/`                                     | Integration, Governance       | GCMP planning, execution, guardrails, and certification report truthful status.                                        |
| GMVS                               | `tests/gmvs/`                                                        | Governance, Contract          | GMVS reports Factory maturity according to its declared validation scope.                                              |


---

## Production Asset Status Rules

Tests must preserve the distinction between:


| Status              | Meaning                                                                                                               |
| ------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `manufactured`      | An asset was generated by a production line.                                                                          |
| `evidence-backed`   | The asset’s applicable assertions are traceable to approved evidence.                                                 |
| `illustrative`      | The asset uses an explicitly labelled example and is not product- or customer-specific.                               |
| `runtime-dependent` | The asset requires real runtime inputs before it can produce a valid result.                                          |
| `blocked`           | The Factory deliberately refuses to manufacture or conclude because required evidence, inputs, or support are absent. |
| `deprecated`        | The asset or contract must not be used for new production work.                                                       |


A test must never assert a stronger status than the asset can truthfully support.

---

## Test Placement Rules

1. New executable tests must be created under `tests/`.
2. Production modules must not contain `test_*.py` files.
3. A new production asset must have at least one canonical contract test before it is registered for execution.
4. A changed production contract must update its canonical test in the same change.
5. Duplicate tests must be removed or explicitly marked as regression fixtures with a documented purpose.
6. Tests must use synthetic or approved sanitized fixtures. Raw insurer documents and sensitive local data must not be committed without approval.

---

## Current Factory Stabilisation Baseline

```text
Test root: tests/
Pytest configuration: pytest.ini
Current result: 126 passed
Legacy duplicate Waiting Period domain test: removed

```

---

## Waiting Period Timeline Capability Status


| Capability                           | Status                                                 |
| ------------------------------------ | ------------------------------------------------------ |
| Timeline engine                      | Built and tested                                       |
| Evidence-profile resolver            | Built and tested                                       |
| Runtime input requirement            | Required: policy start date and claim date             |
| GCMP integration                     | Deferred                                               |
| Product-specific automatic execution | Blocked until a broader evidence-input contract exists |
| Claim approval determination         | Explicitly out of scope                                |


The Waiting Period timeline capability is a reusable platform capability. It is not a generic automatic claim-eligibility engine.