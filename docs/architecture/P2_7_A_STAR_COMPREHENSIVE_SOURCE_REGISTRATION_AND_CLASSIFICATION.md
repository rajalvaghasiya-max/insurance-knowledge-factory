# P2.7-A — Cross-insurer replication: Star Comprehensive source registration and classification

## Purpose
Start the cross-insurer replication pilot without reusing legacy intelligence JSON as source evidence. The pilot registers the actual public PDFs copied into `archive/raw_documents/star_health`, then classifies their reuse eligibility under the existing P2.5-G and P2.5-F3 controls.

## Pilot scope
- Insurer: Star Health and Allied Insurance Company Limited
- Product: Star Comprehensive Insurance Policy
- UIN: `SHAHLIP26044V092526`
- Primary source: 2025 policy wording
- Corroborating source: 2025 prospectus
- Candidate concept for later review: conditional co-payment

## Why this is a source overlay
No Factory code is changed. The existing generic-source registration and document-classification components are reused. Legacy `product_intelligence.json` remains a discovery map only; it is not input evidence for the canonical pipeline.

## Required inputs
The following repository paths must already exist:
- `archive/raw_documents/star_health/star_comprehensive_policy_wording_2025.pdf`
- `archive/raw_documents/star_health/star_comprehensive_prospectus_2025.pdf`

## Registration
Use `scripts.run_generic_source_registration` with the supplied bundle spec. This writes two independently hash-bound registrations plus a bundle record. Candidate excerpts are discovery aids only and require human review.

## Classification
Use `scripts.run_document_classification` with the supplied supplemental manifest. Both documents are reviewed as `reusable_generic` / `reusable_evidence_candidate`. The policy wording is primary legal; the prospectus is corroborating legal.

## Boundaries
- Do not treat prior legacy extractions as canonical evidence.
- Do not register or use customer schedules, quotes, endorsements, or member-specific material.
- Do not publish co-payment yet.
- Do not conclude anything from a feature not explicitly stated in reviewed official evidence.
- Do not replace any prior Star Health legacy artifacts.

## Next decision
After registration/classification, inspect the candidate spans for the co-payment clause in both documents. Only then decide whether a generic conditional-rule binding is supported.
