"""P2.6-A — generic feature applicability and unknown-state contract.

This module records what a reviewed set of official sources supports about a
feature. It deliberately distinguishes an explicit fact from an absence of
reviewed evidence. It does not infer product terms and it does not publish
knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


class FeatureApplicabilityError(ValueError):
    """Raised when an applicability review violates the evidence contract."""


@dataclass(frozen=True)
class FeatureApplicabilityReviewResult:
    assessment: Mapping[str, Any]


_ALLOWED_STATUSES = {
    "explicitly_present",
    "explicitly_not_applicable",
    "not_stated",
    "unknown_pending_evidence",
}


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise FeatureApplicabilityError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise FeatureApplicabilityError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FeatureApplicabilityError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ':' in raw[:3] or '..' in path.parts:
        raise FeatureApplicabilityError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _string_list(value: object, label: str, *, required: bool = False) -> list[str]:
    entries = _items(value, label)
    parsed = [_text(item, f"{label}[]") for item in entries]
    if required and not parsed:
        raise FeatureApplicabilityError(f"{label} must be non-empty")
    if len(parsed) != len(set(parsed)):
        raise FeatureApplicabilityError(f"{label} must not contain duplicates")
    return parsed


def _source_reference_pairs(feature: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    return (
        _string_list(feature.get('evidence_span_ids', []), 'feature.evidence_span_ids'),
        _string_list(feature.get('source_document_version_ids', []), 'feature.source_document_version_ids'),
    )


class FeatureApplicabilityReviewer:
    """Creates a read-only review artifact for product feature applicability."""

    def review_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
        reviewed_at: str | None = None,
    ) -> FeatureApplicabilityReviewResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Feature applicability specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding='utf-8'))
        except Exception as exc:
            raise FeatureApplicabilityError("Feature applicability specification is not valid UTF-8 JSON") from exc
        return self.review(spec=_mapping(spec, 'feature_applicability_spec'), repository_root=repository_root, reviewed_at=reviewed_at)

    def review(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        reviewed_at: str | None = None,
    ) -> FeatureApplicabilityReviewResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")
        if spec.get('schema_version') != '1.0':
            raise FeatureApplicabilityError('feature_applicability_spec.schema_version must be 1.0')
        if spec.get('review_type') != 'generic_feature_applicability_review_v1':
            raise FeatureApplicabilityError('feature_applicability_spec.review_type is invalid')
        if spec.get('reviewed_by_human') is not True:
            raise FeatureApplicabilityError('feature_applicability_spec.reviewed_by_human must be true')

        product_version_id = _text(spec.get('product_version_id'), 'product_version_id')
        reviewed_documents = _string_list(
            spec.get('reviewed_source_document_version_ids'),
            'reviewed_source_document_version_ids',
            required=True,
        )
        raw_features = _items(spec.get('features'), 'features')
        if not raw_features:
            raise FeatureApplicabilityError('features must be non-empty')

        normalized: list[dict[str, Any]] = []
        feature_ids: set[str] = set()
        for index, raw in enumerate(raw_features):
            feature = _mapping(raw, f'features[{index}]')
            feature_id = _text(feature.get('feature_id'), f'features[{index}].feature_id')
            if feature_id in feature_ids:
                raise FeatureApplicabilityError('features.feature_id must be unique')
            feature_ids.add(feature_id)
            status = _text(feature.get('applicability_status'), f'features[{index}].applicability_status')
            if status not in _ALLOWED_STATUSES:
                raise FeatureApplicabilityError(f'unsupported applicability_status for {feature_id}: {status}')

            evidence_span_ids, document_version_ids = _source_reference_pairs(feature)
            base: dict[str, Any] = {
                'feature_id': feature_id,
                'applicability_status': status,
                'review_status': 'reviewed_not_published',
                'product_version_id': product_version_id,
            }

            if status in {'explicitly_present', 'explicitly_not_applicable'}:
                if not evidence_span_ids or not document_version_ids:
                    raise FeatureApplicabilityError(
                        f'{status} requires evidence_span_ids and source_document_version_ids for {feature_id}'
                    )
                if not set(document_version_ids).issubset(set(reviewed_documents)):
                    raise FeatureApplicabilityError(
                        f'source_document_version_ids must be within reviewed_source_document_version_ids for {feature_id}'
                    )
                statement = _text(feature.get('reviewed_statement'), f'features[{index}].reviewed_statement')
                base.update({
                    'reviewed_statement': statement,
                    'evidence_span_ids': evidence_span_ids,
                    'source_document_version_ids': document_version_ids,
                    'evidence_requirement': 'official_source_evidence_present',
                    'eligible_for_evidence_binding': True,
                })
                if status == 'explicitly_present':
                    value = feature.get('value')
                    if value is None or value == '':
                        raise FeatureApplicabilityError(f'explicitly_present requires a value for {feature_id}')
                    base['value'] = value
                else:
                    if feature.get('value') not in (None, '', 'not_applicable'):
                        raise FeatureApplicabilityError(
                            f'explicitly_not_applicable must not carry a substantive value for {feature_id}'
                        )
                    base['value'] = 'not_applicable'

            elif status == 'not_stated':
                if evidence_span_ids or document_version_ids or 'value' in feature:
                    raise FeatureApplicabilityError(
                        f'not_stated must not carry evidence references or a value for {feature_id}'
                    )
                base.update({
                    'reviewed_statement': _text(feature.get('reviewed_statement'), f'features[{index}].reviewed_statement'),
                    'evidence_requirement': 'no_conclusion_from_silence',
                    'eligible_for_evidence_binding': False,
                })

            elif status == 'unknown_pending_evidence':
                if evidence_span_ids or document_version_ids or 'value' in feature:
                    raise FeatureApplicabilityError(
                        f'unknown_pending_evidence must not carry evidence references or a value for {feature_id}'
                    )
                required_types = _string_list(
                    feature.get('required_evidence_types'),
                    f'features[{index}].required_evidence_types',
                    required=True,
                )
                base.update({
                    'reviewed_statement': _text(feature.get('reviewed_statement'), f'features[{index}].reviewed_statement'),
                    'required_evidence_types': required_types,
                    'evidence_requirement': 'official_evidence_required_before_conclusion',
                    'eligible_for_evidence_binding': False,
                })

            normalized.append(base)

        now = reviewed_at or datetime.now(timezone.utc).isoformat()
        assessment = {
            'schema_version': '1.0',
            'artifact_type': 'generic_feature_applicability_assessment_v1',
            'assessment_id': _stable_id('faa', product_version_id, '|'.join(sorted(feature_ids))),
            'assessment_status': 'reviewed_not_published',
            'reviewed_at': now,
            'product_version_id': product_version_id,
            'reviewed_source_document_version_ids': reviewed_documents,
            'features': normalized,
            'guardrails': [
                'Extract only what an official source explicitly supports.',
                'Not mentioned does not mean not applicable, unlimited, nil, or excluded.',
                'Unknown is a valid outcome and must not be converted into a product fact.',
                'This review does not publish knowledge or replace canonical evidence binding.',
            ],
        }
        return FeatureApplicabilityReviewResult(assessment=assessment)

    def write_output(
        self,
        result: FeatureApplicabilityReviewResult,
        *,
        repository_root: str | Path,
        output_path: str | Path,
    ) -> Path:
        root = Path(repository_root).resolve()
        rel = _safe_relative_path(str(output_path), 'output_path')
        target = (root / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise FeatureApplicabilityError('output_path must remain under repository_root') from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.assessment, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        return target
