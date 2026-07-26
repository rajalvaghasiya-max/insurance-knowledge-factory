"""P2.5-K — authoritative publisher for eligible canonical generic legal assertions.

Publishes a separate immutable-derived authoritative artifact and receipt. It never
mutates the source canonical projection or the publication eligibility decision.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

class CanonicalAuthoritativePublisherError(ValueError):
    pass

@dataclass(frozen=True)
class CanonicalAuthoritativePublicationResult:
    artifact: Mapping[str, Any]
    receipt: Mapping[str, Any]

def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict): raise CanonicalAuthoritativePublisherError(f"{label} must be a JSON object")
    return value

def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list): raise CanonicalAuthoritativePublisherError(f"{label} must be a JSON array")
    return value

def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip(): raise CanonicalAuthoritativePublisherError(f"{label} must be a non-empty string")
    return value.strip()

def _safe_relative_path(value: object, label: str) -> str:
    raw=_text(value,label); p=Path(raw)
    if p.is_absolute() or ':' in raw[:3] or '..' in p.parts: raise CanonicalAuthoritativePublisherError(f"{label} must be a safe repository-relative path")
    return p.as_posix()

def _load_json(root: Path, rel: str, label: str) -> tuple[Mapping[str,Any],str]:
    target=(root/rel).resolve()
    try: target.relative_to(root)
    except ValueError as exc: raise CanonicalAuthoritativePublisherError(f"{label} must remain under repository_root") from exc
    if not target.is_file(): raise FileNotFoundError(f"{label} was not found: {rel}")
    raw=target.read_bytes()
    try: data=json.loads(raw.decode('utf-8'))
    except Exception as exc: raise CanonicalAuthoritativePublisherError(f"{label} is not valid UTF-8 JSON") from exc
    return _mapping(data,label), sha256(raw).hexdigest()

def _stable_id(prefix: str,*parts: str)->str:
    return f"{prefix}_{sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]}"

def _serialize_json(data: Mapping[str, Any]) -> bytes:
    """Return the exact UTF-8 bytes used for persisted JSON artifacts."""
    return (json.dumps(data, indent=2, sort_keys=True) + '\n').encode('utf-8')

class CanonicalAuthoritativePublisher:
    def publish_from_spec_file(self, *, spec_path: str|Path, repository_root: str|Path)->CanonicalAuthoritativePublicationResult:
        p=Path(spec_path)
        if not p.is_file(): raise FileNotFoundError(f"Authoritative publication specification was not found: {p}")
        try: spec=json.loads(p.read_text(encoding='utf-8'))
        except Exception as exc: raise CanonicalAuthoritativePublisherError('Authoritative publication specification is not valid JSON') from exc
        return self.publish(spec=_mapping(spec,'authoritative_publication_spec'),repository_root=repository_root)

    def publish(self, *, spec: Mapping[str,Any], repository_root: str|Path, published_at: str|None=None)->CanonicalAuthoritativePublicationResult:
        root=Path(repository_root).resolve()
        if not root.is_dir(): raise FileNotFoundError(f"repository_root was not found: {root}")
        if spec.get('schema_version')!='1.0': raise CanonicalAuthoritativePublisherError('authoritative_publication_spec.schema_version must be 1.0')
        if spec.get('publisher_type')!='canonical_authoritative_publisher_v1': raise CanonicalAuthoritativePublisherError('authoritative_publication_spec.publisher_type is invalid')
        if spec.get('approved_by_human') is not True: raise CanonicalAuthoritativePublisherError('authoritative_publication_spec.approved_by_human must be true')
        projection_path=_safe_relative_path(spec.get('canonical_projection_path'),'canonical_projection_path')
        decision_path=_safe_relative_path(spec.get('publication_decision_path'),'publication_decision_path')
        projection,projection_sha=_load_json(root,projection_path,'canonical_projection')
        decision,decision_sha=_load_json(root,decision_path,'publication_decision')
        report=_mapping(projection.get('projection_report'),'canonical_projection.projection_report')
        if report.get('projection_status')!='validated_read_only_canonical_projection_not_published':
            raise CanonicalAuthoritativePublisherError('canonical projection is not a validated unpublished projection')
        if decision.get('decision_status')!='reviewed_assertions_eligible_not_published':
            raise CanonicalAuthoritativePublisherError('publication decision is not an eligible unpublished decision')
        if decision.get('canonical_projection_sha256')!=projection_sha:
            raise CanonicalAuthoritativePublisherError('publication decision projection hash mismatch')
        requested=[_text(x,'assertion_ids[]') for x in _items(spec.get('assertion_ids'),'assertion_ids')]
        if not requested or len(requested)!=len(set(requested)): raise CanonicalAuthoritativePublisherError('assertion_ids must be non-empty and unique')
        canonical=_mapping(projection.get('canonical_bundle'),'canonical_projection.canonical_bundle')
        assertions={_text(x.get('assertion_id'),'assertion.assertion_id'):_mapping(x,'assertion') for x in _items(canonical.get('assertions'),'canonical_bundle.assertions')}
        eligible={_text(x.get('assertion_id'),'decision.assertion_id'):_mapping(x,'decision') for x in _items(decision.get('decisions'),'publication_decision.decisions')}
        selected=[]
        for aid in requested:
            a=assertions.get(aid); d=eligible.get(aid)
            if a is None: raise CanonicalAuthoritativePublisherError(f'requested assertion is missing: {aid}')
            if d is None or d.get('eligibility_status')!='eligible_for_authoritative_publication': raise CanonicalAuthoritativePublisherError(f'assertion is not eligible for authoritative publication: {aid}')
            if a.get('publication_status')!='unpublished': raise CanonicalAuthoritativePublisherError(f'assertion is not unpublished: {aid}')
            if a.get('validation_status')!='evidence_assembled': raise CanonicalAuthoritativePublisherError(f'assertion is not evidence_assembled: {aid}')
            payload=_mapping(a.get('payload'),'assertion.payload')
            if payload.get('scope')!='reusable_generic_product_legal_condition': raise CanonicalAuthoritativePublisherError(f'assertion scope is not publishable: {aid}')
            rtype=_text(payload.get('rule_type'),'assertion.payload.rule_type')
            if rtype in {'room_category_constraint','room_rent_limit','icu_room_rent_exception','icu_limit'}: raise CanonicalAuthoritativePublisherError(f'entitlement assertion is blocked from this publisher: {aid}')
            selected.append({**a,'publication_status':'authoritative','publication_decision_id':d.get('publication_decision_id')})
        now=published_at or datetime.now(timezone.utc).isoformat()
        product_version=_text(spec.get('product_version_id'),'product_version_id')
        if any(x.get('product_version_id')!=product_version for x in selected): raise CanonicalAuthoritativePublisherError('product_version_id mismatch')
        artifact={
          'schema_version':'1.0','artifact_type':'canonical_authoritative_generic_legal_assertions_v1','authority_mode':'canonical_authoritative_generic_legal_assertions',
          'publication_status':'authoritative','published_at':now,'product_version_id':product_version,
          'source_canonical_projection_path':projection_path,'source_canonical_projection_sha256':projection_sha,
          'source_publication_decision_path':decision_path,'source_publication_decision_sha256':decision_sha,
          'assertions':selected,
          'evidence_spans':[x for x in _items(canonical.get('evidence_spans'),'canonical_bundle.evidence_spans') if any(x.get('evidence_span_id') in a.get('evidence_span_ids',[]) for a in selected)],
          'guardrails':['Published only from eligible canonical generic legal assertions.','Does not publish Plan-specific room category, room-rent limit, or ICU limit entitlements.','Does not mutate canonical projection or publication decision artifacts.']
        }
        artifact_sha=sha256(_serialize_json(artifact)).hexdigest()
        receipt={'schema_version':'1.0','receipt_type':'canonical_authoritative_publication_receipt_v1','published_at':now,'artifact_sha256':artifact_sha,'product_version_id':product_version,'published_assertion_ids':[a['assertion_id'] for a in selected],'source_canonical_projection_sha256':projection_sha,'source_publication_decision_sha256':decision_sha,'publication_status':'authoritative'}
        return CanonicalAuthoritativePublicationResult(artifact=artifact,receipt=receipt)

    def write_outputs(self,result: CanonicalAuthoritativePublicationResult, *, repository_root: str|Path, artifact_output_path: str|Path, receipt_output_path: str|Path)->tuple[Path,Path]:
        root=Path(repository_root).resolve()
        artifact_rel=_safe_relative_path(str(artifact_output_path),'artifact_output_path')
        receipt_rel=_safe_relative_path(str(receipt_output_path),'receipt_output_path')
        artifact_target=(root/artifact_rel).resolve()
        receipt_target=(root/receipt_rel).resolve()
        for label, target in [('artifact_output_path', artifact_target), ('receipt_output_path', receipt_target)]:
            try: target.relative_to(root)
            except ValueError as exc: raise CanonicalAuthoritativePublisherError(f'{label} must remain under repository_root') from exc

        artifact_target.parent.mkdir(parents=True,exist_ok=True)
        artifact_bytes=_serialize_json(result.artifact)
        artifact_target.write_bytes(artifact_bytes)

        # The receipt is intentionally derived from the exact persisted artifact bytes,
        # not from an alternative in-memory JSON serialization.
        receipt=dict(result.receipt)
        receipt['artifact_sha256']=sha256(artifact_bytes).hexdigest()
        receipt_target.parent.mkdir(parents=True,exist_ok=True)
        receipt_target.write_bytes(_serialize_json(receipt))
        return artifact_target,receipt_target
