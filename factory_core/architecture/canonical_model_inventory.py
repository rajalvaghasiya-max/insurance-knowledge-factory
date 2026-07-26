
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
import json

_JSON_EXCLUDED_PARTS = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
_MAX_BYTES = 5_000_000

@dataclass(frozen=True)
class InventoryOptions:
    root: Path
    max_bytes: int = _MAX_BYTES

def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def _artifact_type(path: Path, payload: dict[str, Any]) -> str:
    normalized = path.as_posix().lower()
    keys = set(payload.keys())
    if "rules" in keys and ("conditional_rule" in normalized or "authority_mode" in keys):
        return "conditional_rule_artifact"
    if "publisher_version" in keys or normalized.endswith("_publication_receipt.json"):
        return "publication_receipt"
    if "decision_bearing_candidates" in keys or "triage_version" in keys:
        return "evidence_triage_artifact"
    if "candidates" in keys and ("routing" in normalized or "field" in keys):
        return "routing_artifact"
    if "documents" in keys or "document_versions" in keys or "pdf_registry" in normalized:
        return "document_registry"
    if "products" in keys or "insurers" in keys or "uin" in normalized or "product" in normalized:
        return "product_registry_or_catalog"
    if "evidence" in keys or "evidence_id" in keys:
        return "evidence_artifact"
    return "other_json"

def _safe_scalar(payload: dict[str, Any], key: str) -> Any:
    value = payload.get(key)
    return value if isinstance(value, (str, int, float, bool)) or value is None else None

def _rule_summary(payload: dict[str, Any]) -> dict[str, Any]:
    rules = payload.get("rules")
    if not isinstance(rules, list):
        return {}
    types = Counter(
        str(rule.get("rule_type"))
        for rule in rules
        if isinstance(rule, dict) and rule.get("rule_type") is not None
    )
    evidence_ids: list[str] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        evidence = rule.get("evidence")
        if isinstance(evidence, dict):
            primary = evidence.get("primary_evidence")
            if isinstance(primary, dict) and isinstance(primary.get("evidence_id"), str):
                evidence_ids.append(primary["evidence_id"])
    return {
        "rule_count": len(rules),
        "rule_types": dict(sorted(types.items())),
        "primary_evidence_ids": sorted(set(evidence_ids)),
    }

def _relationship_summary(payload: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "entity_id", "field", "document_id", "source_document_id",
        "product_id", "insurer_id", "uin", "authority_mode",
        "verification_mode", "source_shadow_rules_path",
        "source_legacy_triage_path", "source_verification_report_path",
    )
    return {
        key: _safe_scalar(payload, key)
        for key in fields
        if _safe_scalar(payload, key) is not None
    }

def _iter_json_files(root: Path):
    for path in sorted(root.rglob("*.json")):
        if any(part in _JSON_EXCLUDED_PARTS for part in path.parts):
            continue
        yield path

def build_canonical_model_inventory(options: InventoryOptions) -> dict[str, Any]:
    root = options.root.resolve()
    artifacts: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for path in _iter_json_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            size = path.stat().st_size
            if size > options.max_bytes:
                failures.append({"path": relative, "reason": f"skipped_too_large:{size}"})
                continue
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                failures.append({"path": relative, "reason": "root_not_object"})
                continue
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            failures.append({"path": relative, "reason": type(exc).__name__})
            continue

        artifact = {
            "path": relative,
            "artifact_type": _artifact_type(path, payload),
            "sha256": _sha256_file(path),
            "bytes": size,
            "schema_version": _safe_scalar(payload, "schema_version"),
            "top_level_keys": sorted(payload.keys()),
            "relationships": _relationship_summary(payload),
            "rule_summary": _rule_summary(payload),
        }
        artifacts.append(artifact)

    by_type = Counter(a["artifact_type"] for a in artifacts)
    schema_versions = defaultdict(Counter)
    relationship_fields = Counter()
    rule_types = Counter()
    for artifact in artifacts:
        schema_versions[artifact["artifact_type"]][str(artifact["schema_version"])] += 1
        relationship_fields.update(artifact["relationships"].keys())
        rule_types.update(artifact["rule_summary"].get("rule_types", {}))

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "scope": {
            "included": "JSON artifacts only",
            "excluded_paths": sorted(_JSON_EXCLUDED_PARTS),
            "max_bytes_per_json": options.max_bytes,
            "raw_documents_inspected": False,
            "pii_values_collected": False,
        },
        "summary": {
            "artifact_count": len(artifacts),
            "failure_count": len(failures),
            "artifact_types": dict(sorted(by_type.items())),
            "schema_versions_by_artifact_type": {
                kind: dict(sorted(counts.items()))
                for kind, counts in sorted(schema_versions.items())
            },
            "relationship_fields_observed": dict(sorted(relationship_fields.items())),
            "conditional_rule_types_observed": dict(sorted(rule_types.items())),
        },
        "artifacts": artifacts,
        "failures": failures,
        "next_review_questions": [
            "Which observed artifact types are authoritative versus intermediate?",
            "Which relationship fields need stable IDs rather than file paths?",
            "Which document identifiers can be tied to immutable document versions and hashes?",
            "Which facts and conditional rules need a shared publication-state vocabulary?",
            "Which existing artifacts need adapters rather than a destructive migration?",
        ],
    }
