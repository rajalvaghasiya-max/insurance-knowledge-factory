
from __future__ import annotations
import hashlib, json, re
from typing import Any, Mapping, Sequence

class CopayCustomerDocumentFactError(ValueError): pass

class CopayCustomerDocumentFactContract:
    VERSION="1.0"; SCHEMA_VERSION="1.0"
    RECORD_TYPE="health_customer_copay_fact_v1"
    ALLOWED_STATUSES={"extracted","not_found","ambiguous","blocked"}
    ALLOWED_CUSTOMER_DOCUMENT_TYPES={"policy_schedule","quote","renewal_notice","endorsement"}
    ALLOWED_SELECTION_STATES={"explicitly_selected","single_explicit_applicable_value","option_not_selected","multiple_distinct_values","scope_unresolved","not_evaluated"}
    ALLOWED_APPLICABILITY_STATES={"unconditional","conditional","scope_unresolved","not_evaluated"}
    _SHA=re.compile(r"[0-9a-f]{64}")

    @classmethod
    def build(cls, *, source, status, normalized_value, evidence_items,
              candidate_ids, distinct_candidate_values, status_reason,
              selection_state, applicability_state, copay_modes,
              scope_hints, waiver_signal):
        record={
            "schema_version":"1.0","record_type":cls.RECORD_TYPE,
            "contract_version":"1.0",
            "fact_id":cls._id(source["sha256"],status,normalized_value,candidate_ids,
                              distinct_candidate_values,selection_state,applicability_state,waiver_signal),
            "fact_scope":"customer_specific","concept_id":"copay",
            "field_key":"customer_selected_copay",
            "related_product_field_key":"copay",
            "status":status,"status_reason":status_reason,
            "selection_state":selection_state,
            "applicability_state":applicability_state,
            "copay_modes":sorted(set(copay_modes)),
            "scope_hints":sorted(set(scope_hints)),
            "waiver_signal":waiver_signal,
            "source":dict(source),
            "normalized_value":dict(normalized_value) if normalized_value else None,
            "candidate_count":len(set(candidate_ids)),
            "supporting_candidate_ids":sorted(set(candidate_ids)),
            "distinct_candidate_values":sorted(set(distinct_candidate_values)),
            "evidence_items":sorted(
                [dict(x) for x in evidence_items],
                key=lambda x:(x.get("page_number",0),x.get("character_start",0),x.get("candidate_id",""))
            ),
            "publication_state":"not_published",
            "customer_answer_state":"not_created",
            "entitlement_state":"not_evaluated",
            "recommendation_state":"not_created",
            "guardrails":[
                "customer_copay_fact_not_product_fact",
                "customer_copay_fact_not_customer_answer",
                "copay_applicability_not_inferred_beyond_document"
            ],
        }
        cls.validate(record); return record

    @classmethod
    def validate(cls, r: Mapping[str,Any]):
        if r.get("record_type")!=cls.RECORD_TYPE: raise CopayCustomerDocumentFactError("unsupported record_type")
        if not str(r.get("fact_id","")).startswith("cdfact_"): raise CopayCustomerDocumentFactError("invalid fact_id")
        if r.get("concept_id")!="copay": raise CopayCustomerDocumentFactError("concept_id must be copay")
        if r.get("status") not in cls.ALLOWED_STATUSES: raise CopayCustomerDocumentFactError("unsupported status")
        if r.get("selection_state") not in cls.ALLOWED_SELECTION_STATES: raise CopayCustomerDocumentFactError("unsupported selection_state")
        if r.get("applicability_state") not in cls.ALLOWED_APPLICABILITY_STATES: raise CopayCustomerDocumentFactError("unsupported applicability_state")
        s=r.get("source",{}); sha=s.get("sha256")
        if not isinstance(sha,str) or not cls._SHA.fullmatch(sha) or s.get("source_document_id")!=f"sha256:{sha}":
            raise CopayCustomerDocumentFactError("invalid source provenance")
        ids=r.get("supporting_candidate_ids")
        if not isinstance(ids,list) or any(not str(x).startswith("excand_") for x in ids): raise CopayCustomerDocumentFactError("invalid candidate ids")
        if r.get("candidate_count")!=len(ids): raise CopayCustomerDocumentFactError("candidate_count mismatch")
        vals=r.get("distinct_candidate_values")
        if not isinstance(vals,list) or vals!=sorted(set(vals)): raise CopayCustomerDocumentFactError("invalid distinct values")
        for v in vals:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<v<=100: raise CopayCustomerDocumentFactError("invalid percentage")
        if r["status"]=="extracted":
            n=r.get("normalized_value")
            if not isinstance(n,Mapping) or n.get("kind")!="percentage" or n.get("unit")!="percent" or len(vals)!=1 or n.get("value")!=vals[0]:
                raise CopayCustomerDocumentFactError("invalid extracted percentage")
            if not ids or not r.get("evidence_items"): raise CopayCustomerDocumentFactError("missing lineage")
        elif r.get("normalized_value") is not None:
            raise CopayCustomerDocumentFactError("non-extracted fact cannot set value")
        if r["status"]=="not_found" and (ids or vals or r.get("evidence_items")):
            raise CopayCustomerDocumentFactError("not_found cannot contain candidates")
        for k,v in {"publication_state":"not_published","customer_answer_state":"not_created",
                    "entitlement_state":"not_evaluated","recommendation_state":"not_created"}.items():
            if r.get(k)!=v: raise CopayCustomerDocumentFactError(f"{k} must be {v}")

    @staticmethod
    def _id(sha,status,norm,ids,vals,sel,app,waiver):
        material={"sha":sha,"status":status,"normalized":norm,"ids":sorted(set(ids)),
                  "values":sorted(set(vals)),"selection":sel,"applicability":app,"waiver":waiver}
        return "cdfact_"+hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:20]
