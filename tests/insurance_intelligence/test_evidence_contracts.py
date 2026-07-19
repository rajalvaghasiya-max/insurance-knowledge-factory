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

def test_input_requires_matching_request_id():
    with pytest.raises(EvidenceContractError): build_input(request_id='wrong',reasoning_plan=make_plan(),repository_roots=(str(REGISTRY),))
def test_input_requires_root():
    with pytest.raises(EvidenceContractError): build_input(request_id='req-1',reasoning_plan=make_plan(),repository_roots=())
def test_strict_mode_governed():
    with pytest.raises(EvidenceContractError): build_input(request_id='req-1',reasoning_plan=make_plan(),repository_roots=(str(REGISTRY),),strict_mode='LOOSE')
def test_output_preserves_contract_and_request():
    out=resolve(); assert out.contract_version=='1.0' and out.request_id=='req-1'
def test_confidence_bounded(): assert 0<=resolve().confidence<=1
