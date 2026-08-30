# PolicyScna Generated Capability Map

> **GENERATED — DO NOT EDIT.** Deterministic navigation view of the validated semantic capability catalog plus the committed structural fingerprint baseline. Detailed responsibility, safety invariants, notes and module-level structural evidence remain in their canonical machine sources. This map does not authorize roadmap or next actions.

## Control-plane state

- **Catalog version:** `1.0`
- **Enforcement mode:** `RECONCILIATION`
- **Fingerprint schema:** `1.0`
- **Registered capabilities:** `38`
- **Governed roots:** `capability_control`, `insurance_intelligence`

## Interpretation rules

- Executable code and passing tests remain the highest repository evidence.
- Structural fingerprints bind registered implementation to capabilities; they do not infer semantic authority.
- Ownership boundaries shown here are semantic catalog ownership paths; exact module-level structural evidence remains in the fingerprint manifest/inventory.
- Fingerprints below are 12-character navigation prefixes; the committed fingerprint manifest contains the full digest.
- The semantic catalog remains the detailed source for responsibility, safety invariants, lifecycle, reuse policy, ownership and lineage.
- Execution priorities and authorized next actions belong in the execution ledger / blocker record, not in this map.
- Unregistered governed files remain reconciliation candidates while enforcement mode is `RECONCILIATION`.

## Capabilities by plane

### INSURANCE_INTELLIGENCE_CONTEXT

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.CONTEXT.BUILDER`<br>Governed Context Builder | `ACTIVE` | `REUSE` | Determines context sufficiency only; textual mentions and candidate references do not establish governed insurance identity. | None | `insurance_intelligence/context` | `62bc2359c6e0` |

### INSURANCE_INTELLIGENCE_COVERAGE_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.COVERAGE.REGISTRY`<br>Insurance Intelligence Coverage Registry | `ACTIVE` | `REUSE` | Inventory/readiness authority only; it does not resolve product identity, invent insurance facts, rank products, or authorize recommendations. | None | `insurance_intelligence/coverage_registry` | `67470715a6a3` |

### INSURANCE_INTELLIGENCE_DECISION

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.DECISION.DETERMINISTIC_SAFETY_GATE`<br>Deterministic Decision and Safety Gate | `ACTIVE` | `REUSE` | Underlying deterministic safety-decision engine. In the current canonical path ordinary assertion access is mediated by II.DECISION.AUTHORITY_ENFORCEMENT; this base gate does not independently authorize advisory or recommendation paths. | None | `insurance_intelligence/decision`<br>`insurance_intelligence/contracts/decision.py` | `ad2bd1720ca8` |

### INSURANCE_INTELLIGENCE_DECISION_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.DECISION.AUTHORITY_ENFORCEMENT`<br>Authority-Enforced Decision Gate | `ACTIVE` | `REUSE` | Withholds advisory, mixed, unresolved-authority, clarification and out-of-scope paths before the legacy Decision Gate can be invoked. | None | `insurance_intelligence/authority_enforced_decision_gate.py`<br>`insurance_intelligence/contracts/authority_enforcement.py` | `8cb8e6c21191` |

### INSURANCE_INTELLIGENCE_DECISION_SUPPORT

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.DECISION_SUPPORT.NON_VERDICT_PERSONALIZATION`<br>Governed Non-Verdict Personalized Decision Support | `ACTIVE` | `REUSE` | Decision-support framing and sufficiency authority only. It may block, limit, or project governed comparison evidence relative to confirmed customer context, but it cannot aggregate dimensions into a net product direction, choose a product, rank alternatives, declare suitability, perform needs analysis, or recommend. | None | `insurance_intelligence/decision_support` | `1c241b2b2225` |

### INSURANCE_INTELLIGENCE_EVALUATION

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.EVALUATION.MO021_PIPELINE_BASELINE`<br>MO-021 Deterministic Pipeline Evaluation Baseline | `DISCONNECTED` | `REPAIR` | Historical deterministic evaluation infrastructure only. Its hard-coded stage order predates the current guarded canonical orchestration and therefore cannot establish current end-to-end fitness without repair. | None | `insurance_intelligence/evaluation/runner.py`<br>`insurance_intelligence/evaluation/assertions.py`<br>`insurance_intelligence/evaluation/service.py`<br>`insurance_intelligence/evaluation/scenarios.py`<br>`insurance_intelligence/evaluation/fixtures.py`<br>`insurance_intelligence/contracts/evaluation.py` | `d1c3dcedfeea` |
| `II.EVALUATION.TERMINOLOGY_CONTROLLED_PACK`<br>Controlled Terminology Evaluation Pack | `ACTIVE` | `REUSE` | Evaluation-only authority over the controlled terminology pack; it verifies governed terminology behaviour but does not perform fuzzy matching, semantic inference, ranking, recommendation or LLM generation. | None | `insurance_intelligence/evaluation/terminology_controlled_evaluation.py` | `9b7d0eba589a` |

### INSURANCE_INTELLIGENCE_EVIDENCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.EVIDENCE.GOVERNED_RESOLVER`<br>Governed Evidence Resolver | `ACTIVE` | `REUSE` | Underlying evidence-resolution engine. In the canonical current path it is callable only through II.EVIDENCE.INSTANCE_ENFORCEMENT when instance identity is required; it cannot manufacture identity or bypass that guard. | None | `insurance_intelligence/evidence`<br>`insurance_intelligence/contracts/evidence.py` | `60123aac53f6` |

### INSURANCE_INTELLIGENCE_EVIDENCE_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.EVIDENCE.INSTANCE_ENFORCEMENT`<br>Evidence Instance Enforcement | `ACTIVE` | `REUSE` | Preflight wrapper around evidence resolution; it cannot manufacture evidence or identity. | None | `insurance_intelligence/evidence_instance_enforcement.py`<br>`insurance_intelligence/contracts/evidence_instance_enforcement.py` | `66543ac92888` |
| `II.TOPIC_COMPLETENESS.GOVERNED_EVIDENCE_GATE`<br>Governed Topic Completeness Evidence Gate | `ACTIVE` | `REUSE` | Topic-completeness and explanation-permission authority only; it consumes governed evidence resolver output and registered topic/profile definitions but does not retrieve evidence, infer product facts, resolve product identity, perform claim interpretation, compare products, assess suitability, rank, or recommend. | None | `insurance_intelligence/topic_completeness`<br>`insurance_intelligence/contracts/topic_completeness.py`<br>`insurance_intelligence/contracts/topic_profile.py` | `364e96bb69ac` |

### INSURANCE_INTELLIGENCE_EXPLANATION

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.EXPLANATION.EVIDENCE_LOCKED_GENERATOR`<br>Evidence-Locked Explanation Generator | `ACTIVE` | `REUSE` | Underlying presentation engine only. Current ordinary-assertion entry is mediated by II.EXPLANATION.AUTHORITY_ENFORCEMENT; the generator may not retrieve evidence, reason, alter approved scope, or add recommendation authority. | None | `insurance_intelligence/explanation`<br>`insurance_intelligence/contracts/explanation.py` | `773f44e5d374` |

### INSURANCE_INTELLIGENCE_EXPLANATION_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.EXPLANATION.AUTHORITY_ENFORCEMENT`<br>Authority-Enforced Explanation Entry | `ACTIVE` | `REUSE` | Controls entry into the existing evidence-locked Explanation Generator; it does not add findings or recommendation authority. | None | `insurance_intelligence/authority_enforced_explanation.py` | `38a15b653c1f` |

### INSURANCE_INTELLIGENCE_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.GOVERNANCE.BYPASS_INVENTORY`<br>Certified-Pilot Bypass Inventory | `ACTIVE` | `REUSE` | Repository/runtime safety inventory only; it may identify reachable or deferred bypass paths but cannot authorize recommendation output, alter routing, or certify an otherwise ungoverned path. | None | `insurance_intelligence/bypass_inventory/classifier.py`<br>`insurance_intelligence/contracts/bypass_inventory.py` | `5bddd080b7bb` |

### INSURANCE_INTELLIGENCE_IDENTITY_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.IDENTITY.GOVERNED_PRODUCT_ENTITY_RESOLUTION`<br>Governed Product Entity Resolution | `ACTIVE` | `REUSE` | Runtime product-identity resolution and planner-scope authority only; it does not verify source documents, extract or infer UINs, retrieve product evidence, resolve terminology beyond normalized exact governed matching, assess suitability, compare, rank, or recommend. | None | `insurance_intelligence/entity_resolution` | `09f64dc7c496` |
| `II.INSTANCE.SUFFICIENCY`<br>Instance Sufficiency Guard | `ACTIVE` | `REUSE` | Blocks planning when required instance identity is missing, ambiguous, unresolved or not bound to active context. | None | `insurance_intelligence/instance_sufficiency.py`<br>`insurance_intelligence/contracts/instance_sufficiency.py` | `f04672d59151` |

### INSURANCE_INTELLIGENCE_INTENT

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.INTENT.DETERMINISTIC_ANALYZER`<br>Deterministic Intent Analyzer | `ACTIVE` | `REUSE` | Request interpretation only; it does not establish authoritative insurance facts, resolve governed identity, retrieve evidence, reason about policy meaning, or authorize advisory outcomes. | None | `insurance_intelligence/intent`<br>`insurance_intelligence/contracts/intent.py` | `59b74941cb30` |

### INSURANCE_INTELLIGENCE_KNOWLEDGE_CERTIFICATION

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.RULE_CERTIFICATION.GOVERNED_RUNNER`<br>Governed Rule Certification | `ACTIVE` | `REUSE` | Certification authority over declared governed-rule expectations only; it does not resolve evidence, publish facts, or grant downstream recommendation authority. | None | `insurance_intelligence/rule_certification`<br>`insurance_intelligence/contracts/rule_certification.py` | `dc8a63465899` |

### INSURANCE_INTELLIGENCE_ORCHESTRATION

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.ORCHESTRATION.CANONICAL_GUARDED_ORDER`<br>Canonical Guarded Full-Cycle Orchestration Order | `ACTIVE` | `REUSE` | Structural ordering authority for full-cycle orchestration; guarded stages own delegation to legacy evidence, decision and explanation components. | None | `insurance_intelligence/contracts/full_cycle.py` | `d9afb34903c2` |
| `II.ORCHESTRATION.EXECUTION_RUNTIME`<br>Governed Full-Cycle Execution Runtime | `ACTIVE` | `REUSE` | Execution coordinator only; stage-order authority remains II.ORCHESTRATION.CANONICAL_GUARDED_ORDER and semantic authority remains with each guarded stage capability. | None | `insurance_intelligence/orchestration/service.py`<br>`insurance_intelligence/orchestration/execution_state.py`<br>`insurance_intelligence/orchestration/intelligence_adapters.py`<br>`insurance_intelligence/orchestration/knowledge_adapters.py` | `c905319d02c9` |

### INSURANCE_INTELLIGENCE_PLANNING

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.PLANNING.REASONING_PLANNER`<br>Deterministic Reasoning Planner | `ACTIVE` | `REUSE` | Planning authority only; it may declare required operations but does not retrieve evidence, calculate, interpret clauses, compare products, assess suitability, recommend, or generate answers. | None | `insurance_intelligence/planning`<br>`insurance_intelligence/contracts/reasoning_plan.py` | `2817c821a238` |

### INSURANCE_INTELLIGENCE_PUBLICATION_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.PUBLICATION.AUTHORITATIVE_GATE`<br>Authoritative Publication Gate | `ACTIVE` | `REUSE` | Final authority for creating the governed authoritative-publication record; it cannot upgrade a WITHHOLD/BLOCKED decision or repair mismatched lineage. | None | `insurance_intelligence/authoritative_publication`<br>`insurance_intelligence/contracts/authoritative_publication.py` | `6f1ea7a5450a` |
| `II.PUBLICATION.DECISION`<br>Governed Publication Decision | `ACTIVE` | `REUSE` | Determines publication permission only; it explicitly does not create an authoritative publication record. | None | `insurance_intelligence/publication_decision`<br>`insurance_intelligence/contracts/publication_decision.py` | `48867e699bbf` |

### INSURANCE_INTELLIGENCE_REASONING

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.REASONING.ENGINE`<br>Deterministic Reasoning Engine | `ACTIVE` | `REUSE` | May emit only registered finding types and derivations; it does not authorize recommendation or suitability outcomes. | None | `insurance_intelligence/reasoning` | `2038300449f0` |

### INSURANCE_INTELLIGENCE_RENDERING

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.RENDERING.PROVIDER_INTEGRATION`<br>Rendering Provider Integration Bridge | `ACTIVE` | `REUSE` | Candidate-production bridge only; provider success and legacy fidelity success are insufficient for release without exit-safety PASS. | None | `insurance_intelligence/rendering_provider_integration.py` | `b190a3131543` |

### INSURANCE_INTELLIGENCE_RENDERING_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.RENDERING.EXIT_SAFETY`<br>Rendering Exit Safety | `ACTIVE` | `REUSE` | Final deterministic release authority over optional rendered candidates; failed candidates fall back to the original ResponseAssemblerOutput. | None | `insurance_intelligence/rendering_exit_safety.py`<br>`insurance_intelligence/contracts/rendering_exit.py` | `333202f5c3a6` |

### INSURANCE_INTELLIGENCE_REQUEST_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.AUTHORITY.INTENT_RECONCILIATION`<br>Authority and Intent Reconciliation | `ACTIVE` | `REUSE` | Computes the minimum downstream guard and ordinary-assertion eligibility while preserving clarification and out-of-scope exits. | None | `insurance_intelligence/authority_intent_reconciliation.py`<br>`insurance_intelligence/contracts/authority_intent_reconciliation.py` | `8666706571bb` |
| `II.REQUEST.AUTHORITY_BOUNDARY`<br>Assertion and Advisory Request Authority Boundary | `ACTIVE` | `REUSE` | Raises advisory safety obligations and clarification holds; it may never authorize recommendations or suppress independent intent analysis. | None | `insurance_intelligence/request_authority.py`<br>`insurance_intelligence/contracts/request_authority.py` | `255b75ff2f48` |

### INSURANCE_INTELLIGENCE_RESPONSE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.RESPONSE.ASSEMBLY`<br>Deterministic Response Assembler | `ACTIVE` | `REUSE` | Creates the deterministic deliverable answer baseline; it does not authorize new facts or LLM-originated content. | None | `insurance_intelligence/response` | `d2a5cf42467c` |

### INSURANCE_INTELLIGENCE_TERMINOLOGY

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `II.TERMINOLOGY.GOVERNED_RESOLUTION`<br>Governed Insurance Terminology Resolution | `ACTIVE` | `REUSE` | Terminology-normalization and mapping authority only. It may identify an exact governed concept/term relationship, but it does not establish product applicability, retrieve evidence, interpret policy clauses, compare products, rank options, assess suitability, or recommend. | None | `insurance_intelligence/terminology`<br>`insurance_intelligence/contracts/terminology.py` | `fc0fd561f6ee` |

### LLM_CONTROLLED_EVALUATION

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `LLM.EVALUATION.CONTROLLED_PROVIDER_HARNESS`<br>Controlled LLM Provider Evaluation Harness | `ACTIVE` | `REUSE` | Controlled evaluation execution infrastructure only; it records provider/model behaviour and cannot authorize production answer generation or override deterministic evaluation. | None | `insurance_intelligence/evaluation/provider.py`<br>`insurance_intelligence/evaluation/harness.py`<br>`insurance_intelligence/evaluation/dataset.py` | `a517042ce1ef` |
| `LLM.EVALUATION.DETERMINISTIC_BASELINE`<br>Deterministic LLM Output Evaluator | `ACTIVE` | `REUSE` | Authoritative baseline evaluator within MO-022F controlled experiments; external metrics may inform review but do not replace this verdict. | None | `insurance_intelligence/evaluation/deterministic.py`<br>`insurance_intelligence/contracts/llm_evaluation.py` | `81cf4a3e6850` |
| `LLM.EVALUATION.DISAGREEMENT_ANALYSIS`<br>Deterministic and External Evaluation Disagreement Analysis | `ACTIVE` | `REUSE` | Comparison and review evidence only; the deterministic verdict remains unchanged and authoritative in every disagreement category. | None | `insurance_intelligence/evaluation/disagreement.py` | `04f8ae28b1b9` |
| `LLM.EVALUATION.EXTERNAL_METRIC_ADVISORY`<br>External Metric Advisory Evaluation | `EXPERIMENTAL` | `REUSE` | Advisory experimental signal only; dependency failure, timeout, inconclusive results or metric scores cannot override deterministic evaluation. | None | `insurance_intelligence/evaluation/deepeval.py`<br>`insurance_intelligence/evaluation/hhem.py` | `4892ed5c6d91` |
| `LLM.EVALUATION.HYBRID_RENDERING_BASELINE`<br>Deterministic versus LLM Rendering Baseline Comparison | `ACTIVE` | `REUSE` | Measurement and comparison only; it evaluates hybrid-rendering behaviour but does not release customer text or alter rendering safety authority. | None | `insurance_intelligence/evaluation/llm_baseline.py`<br>`insurance_intelligence/evaluation/baseline_certification.py` | `9e694388fd54` |
| `LLM.EVALUATION.RESPONSIBILITY_DECISION_REPORTING`<br>Bounded LLM Responsibility Decision Reporting | `ACTIVE` | `REUSE` | Produces controlled-evaluation decision evidence only; it does not enable an LLM responsibility, authorize production use or mutate underlying evaluation results. | None | `insurance_intelligence/evaluation/responsibility.py` | `210a7a963f89` |

### LLM_RENDERING

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `LLM.RENDERING.CONTROLLED_HYBRID_RUNTIME`<br>Controlled Hybrid LLM Rendering Runtime | `ACTIVE` | `REUSE` | Reusable controlled candidate-rendering runtime. In the current canonical path its candidate remains subordinate to Rendering Exit Safety and is not the final release authority. | None | `insurance_intelligence/llm`<br>`insurance_intelligence/contracts/llm_rendering.py` | `835b098fcadc` |

### PLATFORM

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `PLATFORM.REPOSITORY_INVENTORY`<br>Repository Structural Inventory | `ACTIVE` | `REUSE` | Structural evidence provider only; it does not decide capability lifecycle, semantic authority, reuse policy, or whether NEW is authorized. | None | `capability_control/inventory.py` | `3099ad5dfdec` |

### PLATFORM_GOVERNANCE

| Capability | Lifecycle | Reuse | Authority role | Lineage | Ownership boundary | Fingerprint |
| --- | --- | --- | --- | --- | --- | --- |
| `PLATFORM.CAPABILITY_CONTROL_PLANE`<br>PolicyScna Capability Control Plane | `ACTIVE` | `REUSE` | Repository architecture-memory integrity control; it does not decide insurance truth or runtime answer content. | None | `capability_control` | `78fdc5878ccc` |
