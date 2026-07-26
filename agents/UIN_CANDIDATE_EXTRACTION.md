# UIN Candidate Extraction

`agents/uin_candidate_extractor.py` is the shared format-validation and provenance component for Indian insurance UIN occurrences.

It detects **labelled** UINs, validates generic structure, and returns candidate records with local evidence. It does not assert that a UIN belongs to a product. Product ownership is a later Product Identity Resolution decision.

## Contract

- Candidate status: `format_valid_candidate`
- Label required: `Product UIN`, `UIN`, `UIN No.`, or `Unique Identification No./Number`
- Placeholder values are rejected.
- Returned evidence includes source context, raw match, surrounding evidence text, and match position.

## Consumers

- `agents/product_signal_extractor.py` emits `uin_candidates` plus legacy `uins` values.
- `agents/knowledge_extractor/extract_product_intelligence.py` stores the selected `metadata.uin_candidate` while retaining `metadata.uin` for compatibility.

A candidate is not a Product Identity record and must not be used as a verified product link without resolver evidence.
