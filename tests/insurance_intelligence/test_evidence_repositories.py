from pathlib import Path
import json
import pytest
from insurance_intelligence.contracts.reasoning_plan import build_plan, build_evidence_requirement
from insurance_intelligence.contracts.evidence import build_input, EvidenceContractError
from insurance_intelligence.evidence.resolver import EvidenceResolver

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/'knowledge/factory/registry_backed'

def make_plan(subject='star_health:star_comprehensive', *, authority='BINDING', version='ANY_GOVERNED', status='READY', mode='INTERPRETIVE', evidence=True):
    reqs=()
    if evidence:
        reqs=(build_evidence_requirement(requirement_id='req_copay',evidence_category='NORMALIZED_PRODUCT_FACT',subject_reference=subject,required=True,authority_requirement=authority,version_requirement=version,reason='resolve conditional copay evidence',requested_by_step='step_1'),)
    return build_plan(request_id='req-1',plan_id='plan-1',plan_type='CLAUSE_IMPACT_PLAN',execution_mode=mode,goal='resolve evidence',expected_outcome='CLAUSE_IMPACT_EXPLANATION',plan_status=status,confidence=.9,required_evidence=reqs)

def resolve(plan=None,**kwargs):
    plan=plan or make_plan()
    inp=build_input(request_id='req-1',reasoning_plan=plan,resolution_context=kwargs.pop('resolution_context',{}),repository_roots=(str(REGISTRY),),strict_mode=kwargs.pop('strict_mode','STRICT'),as_of_date=kwargs.pop('as_of_date',None))
    return EvidenceResolver().resolve(inp)
from insurance_intelligence.evidence.repositories import RegistryBackedRepository,sha256_file

def test_resolves_governed_alias():
    ref,alias=RegistryBackedRepository(REGISTRY).resolve_entity('Star Comprehensive'); assert ref=='star_health:star_comprehensive'
def test_unknown_entity_not_fabricated(): assert RegistryBackedRepository(REGISTRY).resolve_entity('Unknown Gold Ultra')==(None,None)
def test_pilot_reads_real_governed_paths():
    r=RegistryBackedRepository(REGISTRY).load_pilot(); assert r.binding_path.exists() and r.projection_path.exists() and r.source_registration_path.exists()
def test_pilot_statement_is_reviewed_source_fact():
    r=RegistryBackedRepository(REGISTRY).load_pilot(); assert '10% co-payment' in r.statement and 'unsuitable' not in r.statement.lower()
def test_source_hash_preserved():
    r=RegistryBackedRepository(REGISTRY).load_pilot(); assert len(r.source_artifact_sha256)==64
def test_snapshot_is_deterministic():
    repo=RegistryBackedRepository(REGISTRY); assert repo.snapshot_hashes()==repo.snapshot_hashes()
