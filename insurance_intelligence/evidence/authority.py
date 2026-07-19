"""Governed source authority and applicability rules."""
from __future__ import annotations
AUTHORITY_RANK={"POLICY_SCHEDULE":1,"ENDORSEMENT":2,"POLICY_WORDING":3,"CUSTOMER_INFORMATION_SHEET":4,"OFFICIAL_PRODUCT_FILING":5,"PROSPECTUS":6,"OFFICIAL_PRODUCT_PAGE":7,"OFFICIAL_FAQ":8,"BROCHURE":9,"SECONDARY_EXPLANATORY_SOURCE":10}
SOURCE_ALIASES={"policy_wording":"POLICY_WORDING","policy_schedule":"POLICY_SCHEDULE","endorsement":"ENDORSEMENT","cis":"CUSTOMER_INFORMATION_SHEET","customer_information_sheet":"CUSTOMER_INFORMATION_SHEET","prospectus":"PROSPECTUS","brochure":"BROCHURE"}
MINIMUM_RANK={"BINDING":3,"AUTHORITATIVE":6,"OFFICIAL":8,"SUPPORTING":10,"ANY_GOVERNED":10}
def normalize_source_type(value:str)->str: return SOURCE_ALIASES.get(value.lower(),value.upper())
def authority_rank(source_type:str)->int: return AUTHORITY_RANK.get(normalize_source_type(source_type),99)
def satisfies_authority(source_type:str,requirement:str)->bool: return authority_rank(source_type)<=MINIMUM_RANK[requirement]
def prefer_source(a:str,b:str)->str|None:
    ra,rb=authority_rank(a),authority_rank(b)
    if ra==rb:return None
    return a if ra<rb else b
