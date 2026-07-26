"""Narrow, read-only adapters over governed registry-backed artifacts."""
from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from pathlib import Path

def sha256_file(path:Path)->str:
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()
def read_json(path:Path): return json.loads(path.read_text(encoding="utf-8"))
@dataclass(frozen=True)
class PilotRecord:
    entity_reference:str; product_name:str; aliases:tuple[str,...]; topic:str; statement:str; source_type:str; document_id:str; document_version_id:str; page:int|None; excerpt:str|None; source_text_sha256:str; binding_path:Path; binding_sha256:str; projection_path:Path; projection_sha256:str; source_registration_path:Path; source_registration_sha256:str; source_artifact_path:str; source_artifact_sha256:str; effective_from:str|None; effective_to:str|None
class RegistryBackedRepository:
    def __init__(self,root): self.root=Path(root)
    def _star_dir(self): return self.root/'star_health_star_comprehensive'
    def aliases(self):
        d=self._star_dir()
        if not d.exists(): return {}
        return {'star comprehensive':'star_health:star_comprehensive','star comprehensive insurance policy':'star_health:star_comprehensive','star_health:star_comprehensive':'star_health:star_comprehensive'}
    def resolve_entity(self,candidate):
        norm=' '.join(candidate.lower().replace('_',' ').replace(':',' ').split())
        for alias,ref in self.aliases().items():
            if norm==alias.replace(':',' ').replace('_',' ') or alias in norm:return ref,alias
        return None,None
    def load_pilot(self)->PilotRecord:
        d=self._star_dir(); binding=d/'generic_legal_condition_binding/star_health_star_comprehensive_conditional_copayment.json'; projection=d/'generic_legal_condition_canonical_projection/star_health_star_comprehensive_conditional_copayment.canonical.json'; registration=d/'generic_source_registration/policy_wording_registration.json'
        b=read_json(binding); p=read_json(projection); r=read_json(registration)
        assertion=b['assertions'][0]; ev=assertion['evidence'][0]; cb=p['canonical_bundle']; doc=cb['source_documents'][0]; dv=cb['document_versions'][0]
        candidate=next((x for x in r['evidence_review']['candidates'] if x['candidate_id']==ev['candidate_id']),None)
        return PilotRecord('star_health:star_comprehensive',b['product_context']['product_display_name'],('Star Comprehensive','Star Comprehensive Insurance Policy'),'copay',assertion['reviewed_statement'],doc['document_type'],ev['document_id'],ev['document_version_id'],ev.get('source_page'),candidate.get('excerpt') if candidate else None,ev['candidate_text_sha256'],binding,sha256_file(binding),projection,sha256_file(projection),registration,sha256_file(registration),dv['storage_locator'],dv['content_sha256'],dv.get('effective_from'),dv.get('effective_to'))
    def snapshot_hashes(self):
        d=self._star_dir(); return {str(p.relative_to(self.root)):sha256_file(p) for p in sorted(d.rglob('*')) if p.is_file()}
