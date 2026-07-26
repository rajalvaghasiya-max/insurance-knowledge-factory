
from __future__ import annotations
import re
from typing import Mapping
from knowledge_domains.health.extraction_primitives.extraction_candidate_contract import ExtractionCandidateContract, ExtractionCandidateContractError
from .copay_customer_document_fact import CopayCustomerDocumentFactContract, CopayCustomerDocumentFactError

class CopayCustomerFactSelector:
    _SELECTED=re.compile(r"\b(?:selected|chosen|opted)\s+(?:co[-\s]?pay(?:ment)?|copayment)\b|\b(?:co[-\s]?pay(?:ment)?|copayment)\s+(?:selected|chosen|opted)\b",re.I)

    def select(self, candidate_document: Mapping):
        try: ExtractionCandidateContract.validate_document(candidate_document)
        except ExtractionCandidateContractError as e: raise CopayCustomerDocumentFactError(str(e)) from e
        source=dict(candidate_document["source"])
        if str(source.get("document_type","")).lower() not in CopayCustomerDocumentFactContract.ALLOWED_CUSTOMER_DOCUMENT_TYPES:
            return self._build(source,"blocked",None,[],[],"unsupported_customer_document_type","not_evaluated","not_evaluated",[],[],False)
        candidates=[c for c in candidate_document.get("candidates",[]) if self._supported(c)]
        candidates.sort(key=lambda c:(c["evidence"]["page_number"],c["evidence"]["character_start"],c["candidate_id"]))
        if not candidates:
            return self._build(source,"not_found",None,[],[],"no_explicit_copay_percentage_candidate","not_evaluated","not_evaluated",[],[],False)
        values=sorted({c["normalized_value"]["value"] for c in candidates})
        ids=[c["candidate_id"] for c in candidates]
        evidence=[self._evidence(c) for c in candidates]
        modes=sorted({str(c["attributes"].get("copay_mode") or "unspecified") for c in candidates})
        scopes=sorted({str(x) for c in candidates for x in c["attributes"].get("scope_hints",[])})
        waiver=any(c["attributes"].get("waiver_signal") is True for c in candidates)
        selected=any(self._SELECTED.search(c["evidence"]["text"]) for c in candidates)
        option=any(m in {"voluntary_or_option","option_or_discount_related"} for m in modes)
        unresolved="scope_unresolved" in scopes or not scopes
        app="scope_unresolved" if unresolved else "conditional"

        if len(values)>1:
            sel="option_not_selected" if option and not selected else "multiple_distinct_values"
            return self._build(source,"ambiguous",None,evidence,ids,
                "multiple_copay_options_without_customer_selection" if sel=="option_not_selected" else "multiple_distinct_copay_values_found",
                sel,app,modes,scopes,waiver,values)
        if option and not selected:
            return self._build(source,"ambiguous",None,evidence,ids,
                "single_copay_option_found_but_customer_selection_not_established",
                "option_not_selected",app,modes,scopes,waiver,values)
        if waiver:
            return self._build(source,"ambiguous",None,evidence,ids,
                "copay_percentage_and_waiver_signal_both_present",
                "scope_unresolved","scope_unresolved",modes,scopes,True,values)
        return self._build(source,"extracted",candidates[0]["normalized_value"],evidence,ids,
            "single_supported_customer_copay_value_found",
            "explicitly_selected" if selected else "single_explicit_applicable_value",
            app,modes,scopes,False,values)

    def _build(self,source,status,norm,evidence,ids,reason,selection,app,modes,scopes,waiver,values=None):
        return CopayCustomerDocumentFactContract.build(
            source=source,status=status,normalized_value=norm,evidence_items=evidence,
            candidate_ids=ids,distinct_candidate_values=values or [],status_reason=reason,
            selection_state=selection,applicability_state=app,copay_modes=modes,
            scope_hints=scopes,waiver_signal=waiver)

    @staticmethod
    def _supported(c):
        v=c.get("normalized_value"); a=c.get("attributes"); n=v.get("value") if isinstance(v,Mapping) else None
        return c.get("candidate_type")=="copay_percentage" and isinstance(a,Mapping) and isinstance(v,Mapping) and v.get("kind")=="percentage" and v.get("unit")=="percent" and isinstance(n,(int,float)) and not isinstance(n,bool) and 0<n<=100

    @staticmethod
    def _evidence(c):
        e=c["evidence"]
        return {"candidate_id":c["candidate_id"],"page_number":e["page_number"],
                "character_start":e["character_start"],"character_end":e["character_end"],
                "normalized_character_start":e["normalized_character_start"],
                "normalized_character_end":e["normalized_character_end"],
                "evidence_type":e["evidence_type"],"text":e["text"],
                "normalized_value":dict(c["normalized_value"]),
                "attributes":dict(c["attributes"]),"confidence":dict(c["confidence"])}
