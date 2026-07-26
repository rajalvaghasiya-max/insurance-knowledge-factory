from insurance_intelligence.contracts.evidence import RequirementResult
from insurance_intelligence.evidence.sufficiency import evaluate

def rr(status): return RequirementResult('r',status,(),(),None,True,True,True,'NONE',1)
def test_complete(): assert evaluate((rr('SATISFIED'),))==('COMPLETE','RESOLVED')
def test_partial(): assert evaluate((rr('PARTIALLY_SATISFIED'),))==('PARTIAL','PARTIALLY_RESOLVED')
def test_lineage_failure(): assert evaluate((rr('FAILED_LINEAGE'),))==('FAILED_LINEAGE','NOT_RESOLVED')
def test_entity_unresolved(): assert evaluate((rr('ENTITY_UNRESOLVED'),))==('ENTITY_UNRESOLVED','NOT_RESOLVED')
def test_conflict(): assert evaluate((rr('CONFLICTING'),))==('CONFLICTING','CONFLICTING')
