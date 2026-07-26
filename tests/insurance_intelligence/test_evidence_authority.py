from insurance_intelligence.evidence.authority import *
def test_policy_schedule_outranks_wording(): assert authority_rank('POLICY_SCHEDULE')<authority_rank('POLICY_WORDING')
def test_wording_satisfies_binding(): assert satisfies_authority('policy_wording','BINDING')
def test_brochure_does_not_satisfy_binding(): assert not satisfies_authority('BROCHURE','BINDING')
def test_preference_is_deterministic(): assert prefer_source('POLICY_WORDING','BROCHURE')=='POLICY_WORDING'
def test_equal_authority_has_no_preference(): assert prefer_source('POLICY_WORDING','POLICY_WORDING') is None
