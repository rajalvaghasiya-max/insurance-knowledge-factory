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
from insurance_intelligence.evidence.repositories import RegistryBackedRepository

def test_star_copay_pilot_resolves():
    out=resolve(); assert out.resolution_status=='RESOLVED'; assert out.sufficiency=='COMPLETE'; assert len(out.evidence_packages)==1
    e=out.evidence_packages[0]; assert e.governed_entity_reference=='star_health:star_comprehensive'; assert e.page==39; assert e.lineage.lineage_status=='VERIFIED'
def test_candidate_alias_resolves():
    out=resolve(make_plan('product_reference'),resolution_context={'resolved_candidate_references':{'product_reference':'Star Comprehensive'}}); assert out.entity_resolutions[0].governed_reference=='star_health:star_comprehensive'
def test_unknown_entity_fails_closed():
    out=resolve(make_plan('Unknown Health Gold Ultra')); assert out.resolution_status=='NOT_RESOLVED'; assert out.sufficiency=='ENTITY_UNRESOLVED'; assert not out.evidence_packages
def test_authority_insufficient_is_partial():
    out=resolve(make_plan(authority='BINDING')); assert out.requirement_results[0].authority_satisfied

def test_version_unresolved_for_policy_specific():
    out=resolve(make_plan(version='POLICY_SPECIFIC')); assert out.resolution_status=='NOT_RESOLVED'; assert out.sufficiency=='VERSION_UNRESOLVED'
def test_no_requirements_avoids_lookup():
    out=resolve(make_plan(evidence=False)); assert out.resolution_status=='NO_REQUIREMENTS' and not out.evidence_packages
def test_out_of_scope_avoids_lookup():
    out=resolve(make_plan(status='OUT_OF_SCOPE',mode='NO_EXECUTION',evidence=False)); assert out.resolution_status=='OUT_OF_SCOPE'
def test_read_only_byte_identity():
    repo=RegistryBackedRepository(REGISTRY); before=repo.snapshot_hashes(); resolve(); after=repo.snapshot_hashes(); assert before==after
def test_deterministic_output(): assert resolve()==resolve()
def test_evidence_claim_has_no_derived_recommendation():
    claim=resolve().evidence_packages[0].claim.lower(); assert 'recommend' not in claim and 'suitable' not in claim
def test_no_calculated_or_final_answer_fields():
    e=resolve().evidence_packages[0]; assert not hasattr(e,'calculated_value') and not hasattr(e,'final_answer')
def test_requirement_is_preserved(): assert resolve().requirement_results[0].requirement_id=='req_copay'
def test_source_paths_are_preserved():
    e=resolve().evidence_packages[0]; assert e.lineage.binding_reference and e.lineage.projection_reference and e.lineage.source_artifact_path

def test_strict_mode_fails_closed_on_lineage_mismatch(tmp_path):
    import shutil
    source=REGISTRY/'star_health_star_comprehensive'
    target=tmp_path/'star_health_star_comprehensive'
    shutil.copytree(source,target)
    binding=target/'generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json'
    binding.write_bytes(binding.read_bytes()+b'\n')
    plan=make_plan()
    inp=build_input(request_id='req-1',reasoning_plan=plan,repository_roots=(str(tmp_path),),strict_mode='STRICT')
    out=EvidenceResolver().resolve(inp)
    assert out.sufficiency=='FAILED_LINEAGE'
    assert out.resolution_status=='NOT_RESOLVED'
    assert not out.evidence_packages


def test_permissive_mode_reports_partial_lineage_without_claiming_verified(tmp_path):
    import shutil
    source=REGISTRY/'star_health_star_comprehensive'
    target=tmp_path/'star_health_star_comprehensive'
    shutil.copytree(source,target)
    binding=target/'generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json'
    binding.write_bytes(binding.read_bytes()+b'\n')
    plan=make_plan()
    inp=build_input(request_id='req-1',reasoning_plan=plan,repository_roots=(str(tmp_path),),strict_mode='PERMISSIVE')
    out=EvidenceResolver().resolve(inp)
    assert out.resolution_status=='RESOLVED_WITH_LIMITATIONS'
    assert out.evidence_packages[0].lineage.lineage_status=='MISMATCH'
    assert not out.requirement_results[0].lineage_satisfied
