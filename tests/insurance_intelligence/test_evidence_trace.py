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

def test_trace_is_ordered_and_structured():
    t=resolve().resolution_trace; assert [e.sequence for e in t]==list(range(1,len(t)+1)); assert all(e.order_marker for e in t)
def test_trace_contains_lineage_and_completion():
    types=[e.event_type for e in resolve().resolution_trace]; assert 'LINEAGE_VERIFIED' in types and types[-1]=='RESOLUTION_COMPLETED'
def test_trace_has_no_chain_of_thought_field():
    assert all(not hasattr(e,'chain_of_thought') for e in resolve().resolution_trace)
