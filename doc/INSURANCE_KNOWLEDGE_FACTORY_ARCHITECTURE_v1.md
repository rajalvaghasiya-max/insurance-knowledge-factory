# Insurance Knowledge Factory – Architecture Blueprint v1.0

## Document Information


| Item          | Details                                                       |
| ------------- | ------------------------------------------------------------- |
| Document Name | Insurance Knowledge Factory – Architecture Blueprint          |
| Version       | 1.0                                                           |
| Status        | Active                                                        |
| Created By    | Rajal Vaghasiya                                               |
| Purpose       | Preserve architecture, decisions, lessons, and future roadmap |
| Last Updated  | June 2026                                                     |


---

# Table of Contents

1. Executive Summary
2. Problem Statement
3. Vision & Product Strategy
4. Guiding Architectural Principles
5. Current System Architecture
6. Repository Structure
7. Component Catalogue
8. Data Artifacts & Contracts
9. Milestones Achieved
10. Architecture Decision Records (ADR)
11. Current State Assessment
12. Known Gaps & Technical Debt
13. Scaling Strategy
14. Future Roadmap
15. Lessons Learned
16. Appendix

---

# 1. Executive Summary

The Insurance Knowledge Factory was born out of a practical problem faced while building insurance intelligence solutions.

Creating and maintaining an up-to-date insurance knowledge repository required manually visiting insurer websites, downloading brochures, prospectuses, policy wordings, customer information sheets, and extracting details into structured formats.

This process was:

- Time-consuming,
- Difficult to maintain,
- Error-prone,
- Impossible to scale across hundreds of products.

The objective of this initiative is to build an evidence-backed, continuously evolving system capable of:

- Discovering insurance information,
- Acquiring documents,
- Parsing and structuring them,
- Extracting product intelligence,
- Validating extracted facts,
- Measuring coverage,
- Identifying knowledge gaps,
- Continuously improving its own understanding.

Rather than becoming a simple insurance chatbot, the long-term ambition is to establish an Insurance Intelligence Layer that powers advisor tools, recommendation systems, claim intelligence engines, and eventually consumer-facing experiences.

# 2. Vision & Product Strategy

## North Star

Become the AI-powered Insurance Intelligence Layer for advisors, brokers, and eventually consumers.

---

## Strategic Pillars

### Pillar 1 – Insurance Knowledge Brain

Build the most comprehensive, evidence-backed repository of Indian insurance products.

Capabilities include:

- Product understanding,
- Benefit extraction,
- Waiting period intelligence,
- Coverage comparison,
- Product evolution tracking.

---

### Pillar 2 – Recommendation Engine

Transform knowledge into advice.

Capabilities include:

- Need-based recommendations,
- Life-stage recommendations,
- Gap analysis,
- Product comparisons,
- Suitability scoring.

---

### Pillar 3 – Claim Intelligence

Assist users throughout the claim journey.

Capabilities include:

- Claim guidance,
- Documentation support,
- Likelihood analysis,
- Rejection intelligence,
- Claims tracking.

# 4. Guiding Architectural Principles

The Insurance Knowledge Factory is guided by a set of principles designed to ensure scalability, trustworthiness, and maintainability.

---

## 4.1 Evidence Over Hallucination

Insurance products are legal contracts. A single incorrect fact can lead to poor recommendations, claim disputes, regulatory concerns, or loss of trust.

Therefore:

- Every extracted fact should be traceable to source evidence.
- The system should prefer "unknown" over "invented."
- Raw evidence snippets should accompany extracted intelligence wherever possible.

Guiding belief:

> If evidence cannot be found, the system should admit uncertainty.

---

## 4.2 Generic Before Insurer-Specific

The objective is not to build hundreds of insurer-specific extractors.

Instead:

- Generic extraction patterns should be attempted first.
- Insurer-specific rules should only be introduced when absolutely necessary.
- Enhancements made for one insurer should improve extraction quality for all insurers.

Guiding belief:

> Scale is achieved through abstraction, not duplication.

---

## 4.3 Cross-Document Validation

Critical facts should not rely on a single source whenever multiple sources are available.

Examples:

- Waiting periods,
- Room rent limits,
- Copayment clauses,
- Eligibility criteria.

The system should attempt to validate facts using:

- Policy Wordings,
- Prospectuses,
- Customer Information Sheets,
- Brochures.

Guiding belief:

> Trust increases when independent documents agree.

---

## 4.4 Provenance by Design

Every fact should answer:

- What is the value?
- Where did it come from?
- Which page supports it?
- Which other sources validated it?

Guiding belief:

> Intelligence without provenance is opinion.

---

## 4.5 Self-Auditing Systems

The system should continuously evaluate its own outputs.

Mechanisms include:

- Validation reports,
- Coverage reports,
- Quality scoring,
- Conflict detection.

Guiding belief:

> Systems that understand their limitations improve faster.

---

## 4.6 Incremental Evolution

The factory should evolve through small iterations.

Approach:

- Build,
- Validate,
- Observe,
- Improve,
- Repeat.

Avoid:

- Large rewrites,
- Premature optimization,
- Over-engineering.

Guiding belief:

> Small iterations compound into robust systems.

---

## 4.7 Knowledge Asset First

Frontend experiences can evolve.

The knowledge asset is the enduring advantage.

Priority order:

1. Knowledge acquisition,
2. Knowledge quality,
3. Knowledge coverage,
4. User experiences.

Guiding belief:

> Build the asset before the interface.

# 5. Current End-to-End Architecture

The Insurance Knowledge Factory transforms unstructured insurer content into validated, evidence-backed intelligence.

## System Flow

Insurer Websites  
↓  
Discovery  
↓  
Document Acquisition  
↓  
Parsing  
↓  
Evidence Routing  
↓  
Product Intelligence Extraction  
↓  
Validation  
↓  
Coverage Intelligence  
↓  
Knowledge Asset

---

## Stage 1 – Discovery

Objective:

Identify product pages and relevant document links.

Outputs:

- URL queues,
- Product page mappings,
- Live document links.

Techniques:

- Static crawling,
- Browser-assisted discovery.

---

## Stage 2 – Document Acquisition

Objective:

Acquire authoritative insurer documents.

Examples:

- Policy Wordings,
- Prospectuses,
- Brochures,
- Customer Information Sheets,
- Proposal Forms.

Outputs:

Structured document repositories.

---

## Stage 3 – Parsing

Objective:

Convert documents into machine-readable JSON.

Outputs:

Page-level structured representations.

Characteristics:

- Source aware,
- Page aware,
- Insurer agnostic.

---

## Stage 4 – Evidence Routing

Objective:

Identify the most relevant evidence for a requested field.

Characteristics:

- Product-aware,
- Field-aware,
- Source-prioritized.

Outputs:

Routing plans.

---

## Stage 5 – Product Intelligence Extraction

Objective:

Transform evidence into structured product intelligence.

Outputs:

- Metadata,
- Waiting periods,
- Benefits,
- Product facts,
- Discounts,
- Optional covers.

Characteristics:

- Cross-document validation,
- Confidence scoring,
- Provenance.

---

## Stage 6 – Validation

Objective:

Assess extraction quality.

Checks include:

- Missing fields,
- Invalid UINs,
- Low confidence facts,
- Missing validation,
- Conflict detection.

Outputs:

Validation reports.

---

## Stage 7 – Coverage Intelligence

Objective:

Measure completeness of product knowledge.

Outputs:

- Coverage scores,
- Missing fields,
- Product readiness,
- Recommendations.

Outcome:

The system understands what it knows and what it should learn next.

# 6. Repository Structure

The repository is organized around the lifecycle of knowledge creation.

config/  
Global settings and shared configuration.

agents/  
Domain agents responsible for extraction and intelligence generation.

scripts/  
Operational scripts and orchestration utilities.

knowledge/  
Persistent knowledge assets generated by the factory.

archive/  
Raw website captures and downloaded artifacts.

discovery/  
URL queues and discovery outputs.

docs/  
Architecture documents and decision records.

---

## agents/

Examples:

- Product Intelligence Extractor,
- Future Claim Intelligence agents,
- Recommendation agents.

Purpose:

Encapsulate reusable intelligence logic.

---

## scripts/

Examples:

- Discovery runners,
- Validation scripts,
- Coverage audits.

Purpose:

Operationalize workflows.

---

## knowledge/

Stores:

- Parsed documents,
- Product intelligence,
- Validation reports,
- Coverage reports.

Purpose:

Represents the evolving knowledge asset.

---

## archive/

Stores:

- Raw metadata captures,
- Downloaded insurer files.

Purpose:

Provides reproducibility and historical traceability.

---

## docs/

Purpose:

Preserve institutional memory.

Contains:

- Architecture blueprints,
- ADRs,
- Milestone documentation.

# 7. Component Catalogue

This section documents major components, their responsibilities, inputs, outputs, and evolution.

---

# 7.1 Discovery Layer

Purpose:

Locate insurer product pages and supporting documents.

Key Files:

- scripts/run_[discovery.py](http://discovery.py)
- scripts/discover_product_documents_[live.py](http://live.py)
- scripts/discover_product_documents_[browser.py](http://browser.py)

Inputs:

- Insurer configurations,
- Product identifiers,
- Seed URLs.

Outputs:

- URL queues,
- Live document links.

Lessons Learned:

Browser-assisted discovery proved essential due to JavaScript-rendered websites.

---

# 7.2 Document Acquisition Layer

Purpose:

Download authoritative insurer documents.

Inputs:

- Live document links.

Outputs:

- Organized document repositories.

Supported Artifacts:

- Policy Wordings,
- Prospectuses,
- Brochures,
- Proposal Forms,
- Customer Information Sheets.

---

# 7.3 Parsing Layer

Purpose:

Convert acquired documents into structured representations.

Characteristics:

- Page-level parsing,
- Source attribution,
- Insurer agnostic.

Outputs:

Parsed JSON documents.

---

# 7.4 Evidence Router

Evolution:

v0.1 → Broad routing  
v0.2 → Context filtering  
v0.3 → Product-aware routing

Purpose:

Prioritize evidence relevant to a specific field.

Characteristics:

- Source priority,
- Product matching,
- Field awareness.

Outputs:

Routing plans.

---

# 7.5 Product Intelligence Extractor

Current Version:

v0.3

Purpose:

Generate evidence-backed product intelligence.

Capabilities:

- Metadata extraction,
- Waiting periods,
- Product facts,
- Core benefits,
- Discounts,
- Optional covers.

Key Innovations:

- Cross-document validation,
- Confidence scoring,
- Validated-by evidence,
- Provenance.

Outputs:

product_intelligence.json

---

# 7.6 Product Intelligence Validator

Current Version:

v0.4.1

Purpose:

Assess the reliability of extracted intelligence.

Checks:

- Missing facts,
- Invalid UINs,
- Confidence thresholds,
- Validation gaps,
- Conflict detection.

Outputs:

product_intelligence_validation_report.json

Evolution:

v0.4.1 introduced duplicate issue prevention.

---

# 7.7 Coverage Intelligence Engine

Current Version:

v0.1

Purpose:

Measure completeness of knowledge.

Capabilities:

- Section coverage scoring,
- Product readiness classification,
- Missing field identification,
- Improvement recommendations.

Outputs:

product_coverage_report.json

Strategic Importance:

Coverage intelligence transforms extraction into a continuous learning process.

---

# 7.8 Future Components

Planned:

- Portfolio Coverage Dashboard,
- Recommendation Engine,
- Claim Intelligence Engine,
- Continuous Learning Loop,
- Advisor Intelligence Layer.

These components will build upon the validated knowledge asset created by the factory.

# 8. Data Artifacts & Contracts

The Insurance Knowledge Factory produces structured artifacts at every stage. These artifacts are the contracts between pipeline components.

---

## 8.1 Routing Plan

File pattern:

```text
knowledge/health/routing_plans/<entity>_<field>_routing_plan.json

```

Purpose:

Stores candidate evidence sources for a specific product and field.

Used by:

- Evidence Router
- Extractors
- Debugging workflows

Key fields:

```json
{
  "entity_id": "star_health:star_comprehensive",
  "field": "copay",
  "candidates": [],
  "rejected": {},
  "priority": []
}

```

---

## 8.2 Product Intelligence

File pattern:

```text
knowledge/health/<insurer>/<product>/intelligence/product_intelligence.json

```

Purpose:

Stores structured product knowledge extracted from parsed documents.

Contains:

- Metadata
- Eligibility
- Sum insured options
- Waiting periods
- Product facts
- Core benefits
- Discounts
- Optional covers
- Source evidence
- Confidence scores
- Cross-document validation

This is the primary knowledge artifact.

---

## 8.3 Validation Report

File pattern:

```text
knowledge/health/<insurer>/<product>/validation/product_intelligence_validation_report.json

```

Purpose:

Audits the extracted intelligence.

Checks:

- Missing critical facts
- Invalid UIN values
- Low confidence facts
- Missing evidence
- Missing cross-document validation
- Possible conflicts

Produces:

- Score
- Status
- Error count
- Warning count
- Issue list

---

## 8.4 Coverage Report

File pattern:

```text
knowledge/health/<insurer>/<product>/coverage/product_coverage_report.json

```

Purpose:

Measures completeness of product knowledge.

Contains:

- Section-wise coverage
- Overall coverage score
- Product readiness status
- Missing fields
- Recommendations

This artifact tells the factory what it still needs to learn.

# 9. Milestones Achieved

## M1 – Knowledge Extraction Engine

Outcome:

The system successfully moved from raw insurer content to structured product intelligence.

Capabilities proven:

- Product document discovery
- Document downloading
- PDF parsing
- Rule-based extraction
- Evidence-backed product facts

Validated using:

- Aditya Birla Health – Activ One
- Star Health – Star Comprehensive

---

## M2 – Self-Auditing Knowledge Factory

Outcome:

The system became capable of evaluating extraction quality.

Capabilities added:

- Product intelligence validation
- Missing metadata detection
- Invalid UIN detection
- Low confidence detection
- Missing source detection
- Missing cross-document validation detection

This marked the transition from simple extraction to self-auditing intelligence.

---

## M2.1 – Validator Deduplication

Outcome:

Validator duplicate warnings were removed.

Before:

- Duplicate warnings inflated issue counts.

After:

- Only unique issues are reported.

This improved trust in validation scores.

---

## M3 – Coverage Intelligence Engine

Outcome:

The system became aware of product knowledge completeness.

Capabilities added:

- Section-wise coverage scoring
- Overall coverage scoring
- Product readiness classification
- Missing field detection
- Improvement recommendations

This created a feedback loop for future extraction improvements.

# 10. Architecture Decision Records

## ADR-001: Evidence-Backed Extraction Over Summarization

Decision:

The system will extract structured facts with evidence instead of relying only on generic AI summaries.

Reason:

Insurance facts are high-stakes and must be traceable.

Implication:

Every critical fact should include source document, page number, raw evidence, confidence score, and validation status.

---

## ADR-002: Generic Extractors Before Insurer-Specific Extractors

Decision:

Build generic extraction logic first.

Reason:

Insurer-specific extractors do not scale.

Implication:

Enhancements should improve the common extraction framework unless insurer-specific behavior is unavoidable.

---

## ADR-003: Cross-Document Validation for Critical Facts

Decision:

Critical facts should be validated across multiple documents wherever possible.

Examples:

- Waiting periods
- Copayment
- Room rent
- Eligibility
- UIN

Reason:

Agreement across documents increases confidence.

---

## ADR-004: Validation Is Separate From Extraction

Decision:

Extractor generates facts. Validator audits facts.

Reason:

Mixing extraction and validation would make the system difficult to reason about.

Implication:

Validation logic should not re-extract facts. It should inspect generated intelligence.

---

## ADR-005: Coverage Intelligence Guides Future Work

Decision:

Coverage reports will guide what the factory improves next.

Reason:

As products scale, manual inspection becomes impossible.

Implication:

Missing fields and low-coverage sections become the roadmap for extractor evolution.

# 11. Current State Assessment

As of Architecture Blueprint v1.0, the Insurance Knowledge Factory has transitioned from a proof of concept into a functioning intelligence pipeline.

## Capabilities Successfully Demonstrated

### Knowledge Acquisition

✓ Static discovery of insurer websites

✓ Browser-assisted discovery for JavaScript-heavy websites

✓ Live document link extraction

✓ Product-specific document acquisition

---

### Document Processing

✓ PDF ingestion

✓ Page-level parsing

✓ Source attribution

✓ Structured JSON generation

---

### Evidence Intelligence

✓ Product-aware evidence routing

✓ Source prioritization

✓ Context filtering

✓ Candidate rejection tracking

---

### Product Intelligence

✓ Metadata extraction

✓ Waiting period extraction

✓ Product fact extraction

✓ Core benefit extraction

✓ Optional cover extraction

✓ Discount extraction

---

### Trust & Quality

✓ Cross-document validation

✓ Confidence scoring

✓ Source provenance

✓ Self-auditing validation

✓ Duplicate issue prevention

---

### Coverage Awareness

✓ Section-wise coverage scoring

✓ Product readiness classification

✓ Missing field detection

✓ Improvement recommendations

---

## Products Successfully Validated

### Aditya Birla Health – Activ One

Status:

USABLE_WITH_REVIEW

Coverage:

Approximately 75%

Validator Score:

85

---

### Star Health – Star Comprehensive

Status:

READY

Coverage:

Approximately 90%

Validator Score:

75

---

## Strategic Assessment

The project has successfully answered the original question:

> Can a continuously evolving, evidence-backed insurance knowledge factory be built?

The answer is:

> Yes.
>
> # 12. Known Gaps & Technical Debt
>
> The following items are known limitations and opportunities for improvement.
>
> ---
>
> ## UIN Extraction Robustness
>
> Issue:
>
> Placeholder values can occasionally be extracted.
>
> Impact:
>
> Metadata quality degradation.
>
> Priority:
>
> High.
>
> Planned Solution:
>
> Introduce stronger regex validation and source prioritization.
>
> ---
>
> ## Eligibility Extraction Variability
>
> Issue:
>
> Different insurers present eligibility information differently.
>
> Impact:
>
> Reduced extraction consistency.
>
> Priority:
>
> Medium.
>
> Planned Solution:
>
> Expand generic extraction patterns.
>
> ---
>
> ## Discount Detection
>
> Issue:
>
> Discount descriptions vary significantly.
>
> Impact:
>
> Coverage variability.
>
> Priority:
>
> Medium.
>
> Planned Solution:
>
> Introduce richer discount extraction heuristics.
>
> ---
>
> ## Coverage Schema Expansion
>
> Issue:
>
> The expected coverage schema remains incomplete.
>
> Missing examples:
>
> - OPD Cover
> - Consumables Cover
> - Modern Treatments
> - Cumulative Bonus
> - Disease Management Programs
>
> Priority:
>
> High.
>
> Planned Solution:
>
> Continuously evolve the schema based on new discoveries.
>
> ---
>
> ## Historical Tracking
>
> Issue:
>
> Product evolution over time is not yet captured.
>
> Priority:
>
> Medium.
>
> Future Capability:
>
> Change detection and version tracking.
>
> ---
>
> ## Portfolio Visibility
>
> Issue:
>
> Coverage is currently assessed at the product level only.
>
> Priority:
>
> High.
>
> Planned Solution:
>
> Portfolio Coverage Dashboard.

# 13. Scaling Strategy

The Insurance Knowledge Factory is designed to evolve incrementally.

---

## Phase 1 – Foundation

Scope:

5 insurers

20 products

Objectives:

- Validate architecture
- Prove generic extraction
- Establish quality mechanisms

Status:

Completed.

---

## Phase 2 – Controlled Expansion

Scope:

20–50 insurers

100–200 products

Objectives:

- Improve extractor generalization
- Expand coverage schemas
- Introduce portfolio visibility
- Reduce manual intervention

Status:

Planned.

---

## Phase 3 – National Knowledge Asset

Scope:

Entire Indian insurance market.

Objectives:

- Continuous document refresh
- Historical tracking
- Product evolution intelligence
- Automated quality improvement

Status:

Future.

---

## Scaling Philosophy

The objective is not to eliminate humans entirely.

Instead:

> Automate the repetitive work and focus human attention only where uncertainty remains.

# 14. Future Roadmap

## M3.1 – Portfolio Coverage Dashboard

Purpose:

Understand knowledge maturity across all products.

Capabilities:

- Portfolio readiness
- Coverage distribution
- Top missing fields
- Improvement prioritization

---

## M4 – Product Comparison Engine

Purpose:

Enable evidence-backed product comparisons.

Capabilities:

- Feature comparison
- Waiting period comparison
- Benefit differentiation
- Advisor-facing intelligence

---

## M5 – Recommendation Engine

Purpose:

Convert knowledge into advice.

Capabilities:

- Need analysis
- Suitability scoring
- Life-stage recommendations
- Coverage gap analysis

---

## M6 – Claim Intelligence Engine

Purpose:

Support claim journeys.

Capabilities:

- Claim guidance
- Documentation support
- Rejection intelligence
- Claims tracking

---

## M7 – Continuous Learning Loop

Purpose:

Enable self-improving intelligence.

Capabilities:

- Learning from coverage gaps
- Learning from validation failures
- Prioritized extraction improvements

---

## M8 – Advisor Intelligence Layer

Purpose:

Deliver knowledge through practical advisor workflows.

Capabilities:

- Product insights
- Comparison tools
- Recommendation support
- Client servicing intelligence

# 15. Lessons Learned

## Browser Discovery Is Essential

Modern insurer websites frequently rely on JavaScript.

Static crawling alone is insufficient.

---

## Generic Extraction Is Feasible

The same extraction framework successfully operated across multiple insurers.

This was one of the project's largest uncertainties.

---

## Validation Improves Trust

Extraction alone is not enough.

Self-auditing mechanisms significantly improve reliability.

---

## Coverage Reveals Blind Spots

Coverage intelligence transformed unknown weaknesses into actionable roadmaps.

---

## Small Iterations Compound

The project progressed through many small improvements rather than large rewrites.

This approach reduced risk and accelerated learning.

---

## Build the Asset First

User experiences can evolve.

The enduring advantage is the knowledge asset itself.

This principle shaped every architectural decision.

# 16. Appendix

## Milestone Summary

M1

Knowledge Extraction Engine

---

M2

Self-Auditing Knowledge Factory

---

M2.1

Validator Deduplication

---

M3

Coverage Intelligence Engine

---

## Glossary

Evidence Routing

Process of identifying the most relevant supporting evidence for a fact.

---

Cross-Document Validation

Verification of facts using multiple independent sources.

---

Coverage Intelligence

Measurement of completeness of extracted knowledge.

---

Product Readiness

Assessment of whether extracted intelligence is sufficiently complete and trustworthy for downstream use.

---

Knowledge Asset

The collection of structured, validated, evidence-backed insurance intelligence produced by the factory.

---

## Closing Reflection

The Insurance Knowledge Factory began as an attempt to reduce manual effort involved in maintaining insurance product knowledge.

It evolved into a system capable of discovering information, validating itself, identifying its own blind spots, and continuously improving its understanding.

The most significant realization throughout this journey was that the real asset is not the interface or the automation scripts.

The real asset is the trusted intelligence layer that sits beneath them.

This document preserves not only what was built, but why it was built this way, ensuring that future iterations remain aligned with the original vision.



# 17. Identity Layer

The Identity Layer provides stable, authoritative identification for insurance products inside the Insurance Knowledge Factory.

As the factory scales, product identity becomes as important as extraction accuracy. Product names can vary across brochures, websites, policy wordings, and customer information sheets. However, the IRDAI UIN provides a stronger regulatory identifier.

---

## 17.1 Purpose

The Identity Layer helps the factory answer:

- Which regulated product is this?

- Is this product already known?

- Is this a new version of an existing product?

- Can uploaded customer policies be matched to known product intelligence?

- Can product facts be reconciled with regulator-level identifiers?

---

## 17.2 Identity Hierarchy

Recommended identity hierarchy:

```text

IRDAI UIN

    ↓

entity_id

    ↓

insurer_slug

    ↓

product_slug

    ↓

product aliases