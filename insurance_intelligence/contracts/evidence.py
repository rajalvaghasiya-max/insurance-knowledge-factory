"""Executable contracts for the governed Evidence Resolver (MO-016)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence
from insurance_intelligence.contracts.reasoning_plan import ReasoningPlan

SUPPORTED_CONTRACT_VERSION = "1.0"
STRICT_MODES=frozenset({"STRICT","PERMISSIVE"})
EVIDENCE_ROLES=frozenset({"SUPPORTING","CONTRADICTING","QUALIFYING","DEFINING","CALCULATION_INPUT","BACKGROUND","SUPERSEDED","INAPPLICABLE"})
ENTITY_RESOLUTION_STATUSES=frozenset({"RESOLVED","RESOLVED_WITH_LIMITATIONS","AMBIGUOUS","NOT_FOUND","CONFLICTING"})
DOCUMENT_RESOLUTION_STATUSES=frozenset({"RESOLVED","RESOLVED_WITH_LIMITATIONS","VERSION_UNRESOLVED","ENTITY_UNRESOLVED","NOT_FOUND","FAILED_LINEAGE","SUPERSEDED_ONLY"})
APPLICABILITY_STATUSES=frozenset({"APPLICABLE","POSSIBLY_APPLICABLE","NOT_APPLICABLE","DATE_UNRESOLVED","VARIANT_UNRESOLVED","POLICY_SPECIFIC_OVERRIDE","SUPERSEDED"})
LINEAGE_STATUSES=frozenset({"VERIFIED","PARTIAL","MISSING","MISMATCH","NOT_REQUIRED"})
REQUIREMENT_STATUSES=frozenset({"SATISFIED","SATISFIED_WITH_LIMITATIONS","PARTIALLY_SATISFIED","CONFLICTING","MISSING","ENTITY_UNRESOLVED","VERSION_UNRESOLVED","FAILED_LINEAGE","NOT_APPLICABLE"})
SUFFICIENCY_STATUSES=frozenset({"COMPLETE","SUFFICIENT","PARTIAL","CONFLICTING","MISSING","STALE","ENTITY_UNRESOLVED","VERSION_UNRESOLVED","FAILED_LINEAGE"})
RESOLUTION_STATUSES=frozenset({"RESOLVED","RESOLVED_WITH_LIMITATIONS","PARTIALLY_RESOLVED","CONFLICTING","NOT_RESOLVED","OUT_OF_SCOPE","NO_REQUIREMENTS","INVALID_INPUT"})
CONFLICT_TYPES=frozenset({"SOURCE_DISAGREEMENT","VERSION_CONFLICT","SCOPE_CONFLICT","ENTITY_CONFLICT","NORMALIZED_FACT_SOURCE_CONFLICT","POLICY_OVERRIDE_CONFLICT"})
CONFLICT_RESOLUTION_STATUSES=frozenset({"RESOLVED_BY_AUTHORITY","RESOLVED_BY_VERSION","RESOLVED_BY_SCOPE","RESOLVED_BY_POLICY_OVERRIDE","UNRESOLVED","REQUIRES_POLICY_SCHEDULE","REQUIRES_HUMAN_REVIEW"})
TRACE_EVENT_TYPES=frozenset({"REQUIREMENT_RECEIVED","ENTITY_CANDIDATE_FOUND","ENTITY_RESOLVED","ENTITY_REJECTED","DOCUMENT_CANDIDATE_FOUND","DOCUMENT_SELECTED","DOCUMENT_REJECTED","VERSION_SELECTED","VERSION_REJECTED","LINEAGE_VERIFIED","LINEAGE_FAILED","EVIDENCE_PACKAGED","CONFLICT_DETECTED","CONFLICT_RESOLVED","SUFFICIENCY_EVALUATED","RESOLUTION_COMPLETED"})

class EvidenceContractError(ValueError): pass

def _s(v,label):
    if not isinstance(v,str) or not v.strip(): raise EvidenceContractError(f"{label} must be a non-empty string")
    return v
def _m(v,allowed,label):
    v=_s(v,label)
    if v not in allowed: raise EvidenceContractError(f"{label} must be one of {sorted(allowed)}")
    return v
def _f(v,label):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<=float(v)<=1: raise EvidenceContractError(f"{label} must be between 0 and 1")
    return float(v)

@dataclass(frozen=True)
class EvidenceResolverInput:
    contract_version:str; request_id:str; reasoning_plan:ReasoningPlan; resolution_context:Mapping[str,object]; repository_roots:tuple[str,...]; as_of_date:str|None; strict_mode:str

def build_input(*,contract_version=SUPPORTED_CONTRACT_VERSION,request_id,reasoning_plan,resolution_context=None,repository_roots=(),as_of_date=None,strict_mode="STRICT"):
    if contract_version!=SUPPORTED_CONTRACT_VERSION: raise EvidenceContractError("unsupported contract_version")
    if not isinstance(reasoning_plan,ReasoningPlan): raise EvidenceContractError("reasoning_plan must be a validated ReasoningPlan")
    request_id=_s(request_id,"request_id")
    if reasoning_plan.request_id!=request_id: raise EvidenceContractError("request_id must match reasoning_plan")
    if not repository_roots: raise EvidenceContractError("repository_roots must not be empty")
    if as_of_date: date.fromisoformat(as_of_date)
    return EvidenceResolverInput(contract_version,request_id,reasoning_plan,dict(resolution_context or {}),tuple(map(str,repository_roots)),as_of_date,_m(strict_mode,STRICT_MODES,"strict_mode"))

@dataclass(frozen=True)
class Lineage:
    source_artifact_path:str; source_artifact_sha256:str; governed_record_path:str; governed_record_sha256:str; binding_reference:str; projection_reference:str; lineage_status:str
@dataclass(frozen=True)
class EntityResolution:
    candidate_reference:str; governed_reference:str|None; resolution_status:str; resolution_basis:str; matched_alias:str|None; confidence:float; alternatives:tuple[str,...]; limitations:tuple[str,...]
@dataclass(frozen=True)
class DocumentResolution:
    document_reference:str; source_type:str; entity_reference:str; version:str; currentness_status:str; effective_from:str|None; effective_to:str|None; lineage_status:str; resolution_basis:str; resolution_status:str
@dataclass(frozen=True)
class EvidencePackage:
    evidence_id:str; requirement_id:str; subject_reference:str; governed_entity_reference:str; field_or_topic:str; claim:str; evidence_role:str; source_type:str; document_reference:str; document_version:str; effective_from:str|None; effective_to:str|None; page:int|None; section:str|None; source_excerpt:str|None; normalized_fact_reference:str|None; authority_rank:int; authority_requirement:str; version_status:str; applicability_status:str; lineage:Lineage; retrieval_basis:tuple[str,...]; confidence:float
@dataclass(frozen=True)
class RequirementResult:
    requirement_id:str; status:str; matched_evidence_ids:tuple[str,...]; rejected_candidate_ids:tuple[str,...]; missing_reason:str|None; authority_satisfied:bool; version_satisfied:bool; lineage_satisfied:bool; conflict_status:str; confidence:float
@dataclass(frozen=True)
class EvidenceConflict:
    conflict_id:str; topic:str; evidence_ids:tuple[str,...]; conflict_type:str; preferred_evidence_id:str|None; preference_basis:str|None; resolution_status:str; materiality:str
@dataclass(frozen=True)
class TraceEvent:
    trace_id:str; sequence:int; event_type:str; requirement_id:str|None; subject_reference:str|None; repository:str|None; candidate_reference:str|None; decision:str; basis:str; source_paths:tuple[str,...]; order_marker:str
@dataclass(frozen=True)
class EvidenceResolverOutput:
    contract_version:str; request_id:str; resolution_id:str; evidence_packages:tuple[EvidencePackage,...]; requirement_results:tuple[RequirementResult,...]; entity_resolutions:tuple[EntityResolution,...]; document_resolutions:tuple[DocumentResolution,...]; conflicts:tuple[EvidenceConflict,...]; missing_evidence:tuple[str,...]; sufficiency:str; limitations:tuple[str,...]; resolution_trace:tuple[TraceEvent,...]; resolution_status:str; confidence:float

def validate_output(o:EvidenceResolverOutput)->EvidenceResolverOutput:
    if o.contract_version!=SUPPORTED_CONTRACT_VERSION: raise EvidenceContractError("unsupported output contract_version")
    _s(o.request_id,"request_id"); _s(o.resolution_id,"resolution_id"); _m(o.sufficiency,SUFFICIENCY_STATUSES,"sufficiency"); _m(o.resolution_status,RESOLUTION_STATUSES,"resolution_status"); _f(o.confidence,"confidence")
    evid={e.evidence_id for e in o.evidence_packages}
    if len(evid)!=len(o.evidence_packages): raise EvidenceContractError("evidence_ids must be unique")
    req={r.requirement_id for r in o.requirement_results}
    for e in o.evidence_packages:
        if e.requirement_id not in req: raise EvidenceContractError("evidence references unknown requirement")
        _m(e.evidence_role,EVIDENCE_ROLES,"evidence_role"); _m(e.lineage.lineage_status,LINEAGE_STATUSES,"lineage_status"); _m(e.applicability_status,APPLICABILITY_STATUSES,"applicability_status"); _f(e.confidence,"evidence confidence")
    for c in o.conflicts:
        if not set(c.evidence_ids)<=evid: raise EvidenceContractError("conflict references unknown evidence")
        _m(c.conflict_type,CONFLICT_TYPES,"conflict_type"); _m(c.resolution_status,CONFLICT_RESOLUTION_STATUSES,"conflict resolution_status")
    for t in o.resolution_trace: _m(t.event_type,TRACE_EVENT_TYPES,"trace event_type")
    return o
