
from knowledge_domains.health.customer_document_intelligence.copay_concept_understanding_matcher import CopayConceptUnderstandingMatcher
SHA="b"*64
def fact(status="extracted"):
    return {"record_type":"health_customer_copay_fact_v1","fact_id":"cdfact_123","fact_scope":"customer_specific",
    "concept_id":"copay","field_key":"customer_selected_copay","status":status,
    "selection_state":"explicitly_selected","applicability_state":"scope_unresolved",
    "scope_hints":["scope_unresolved"],"normalized_value":{"kind":"percentage","value":20,"unit":"percent"},
    "source":{"source_document_id":f"sha256:{SHA}","sha256":SHA}}
def asset(status="certified_candidate",concept="copay",refs=True):
    return {"asset_id":"ua_copay_123","asset_type":"understanding_asset","status":status,"concept_id":concept,
    "traceability":{"meaning_asset_id":"meaning_copay","learning_primitive_collection_id":"lpc_copay",
    "learning_path_collection_id":"lpathc_copay","source_evidence_refs":["copay_definition_v1"] if refs else []}}
def test_match(): assert CopayConceptUnderstandingMatcher().match(customer_fact=fact(),understanding_asset=asset())["status"]=="matched"
def test_ambiguous_not_matchable(): assert CopayConceptUnderstandingMatcher().match(customer_fact=fact("ambiguous"),understanding_asset=asset())["status"]=="not_matchable"
def test_legacy_asset_blocked(): assert CopayConceptUnderstandingMatcher().match(customer_fact=fact(),understanding_asset=asset(refs=False))["status_reason"]=="understanding_asset_lacks_governed_evidence_traceability"
def test_uncertified_blocked(): assert CopayConceptUnderstandingMatcher().match(customer_fact=fact(),understanding_asset=asset(status="PASS"))["status"]=="not_matchable"
def test_mismatch(): assert CopayConceptUnderstandingMatcher().match(customer_fact=fact(),understanding_asset=asset(concept="deductible"))["status"]=="concept_mismatch"
def test_deterministic():
    m=CopayConceptUnderstandingMatcher()
    assert m.match(customer_fact=fact(),understanding_asset=asset())["match_id"]==m.match(customer_fact=fact(),understanding_asset=asset())["match_id"]
