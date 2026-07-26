
from __future__ import annotations
import hashlib, json
from typing import Mapping

class CopayConceptUnderstandingMatchError(ValueError): pass

class CopayConceptUnderstandingMatcher:
    def match(self, *, customer_fact: Mapping, understanding_asset: Mapping, understanding_asset_path=None):
        if customer_fact.get("record_type")!="health_customer_copay_fact_v1" or customer_fact.get("concept_id")!="copay":
            raise CopayConceptUnderstandingMatchError("unsupported customer fact")
        if understanding_asset.get("asset_type")!="understanding_asset" or not str(understanding_asset.get("asset_id","")).startswith("ua_"):
            raise CopayConceptUnderstandingMatchError("invalid understanding asset")
        if customer_fact.get("status")!="extracted":
            status,reason="not_matchable","customer_fact_is_not_extracted"
        elif understanding_asset.get("concept_id")!="copay":
            status,reason="concept_mismatch","customer_fact_concept_does_not_match_understanding_asset"
        elif understanding_asset.get("status")!="certified_candidate":
            status,reason="not_matchable","understanding_asset_is_not_certified_candidate"
        elif not isinstance(understanding_asset.get("traceability"),Mapping) or not understanding_asset["traceability"].get("source_evidence_refs"):
            status,reason="not_matchable","understanding_asset_lacks_governed_evidence_traceability"
        else:
            status,reason="matched","copay_customer_fact_matches_governed_understanding_asset"
        asset_id=understanding_asset.get("asset_id")
        digest=hashlib.sha256(json.dumps({"fact":customer_fact["fact_id"],"status":status,"asset":asset_id},sort_keys=True,separators=(",",":")).encode()).hexdigest()[:20]
        result={
            "schema_version":"1.0","record_type":"health_customer_fact_understanding_match_v1",
            "contract_version":"1.0","match_id":"cumatch_"+digest,"status":status,
            "status_reason":reason,"concept_id":"copay",
            "customer_fact":{"fact_id":customer_fact["fact_id"],"fact_scope":"customer_specific",
                "field_key":customer_fact["field_key"],"status":customer_fact["status"],
                "normalized_value":customer_fact.get("normalized_value"),
                "selection_state":customer_fact.get("selection_state"),
                "applicability_state":customer_fact.get("applicability_state"),
                "scope_hints":list(customer_fact.get("scope_hints") or []),
                "source_document_id":customer_fact["source"]["source_document_id"],
                "source_sha256":customer_fact["source"]["sha256"]},
            "understanding_asset":{"asset_id":asset_id,"asset_type":understanding_asset.get("asset_type"),
                "status":understanding_asset.get("status"),"concept_id":understanding_asset.get("concept_id"),
                "path":understanding_asset_path,"traceability":dict(understanding_asset.get("traceability") or {})},
            "publication_state":"not_published","customer_answer_state":"not_created",
            "entitlement_state":"not_evaluated","recommendation_state":"not_created",
            "guardrails":["match_artifact_not_customer_answer","copay_scope_and_selection_preserved"]
        }
        return result
