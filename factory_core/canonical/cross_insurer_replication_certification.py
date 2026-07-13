"""P2.7-G — reproducible certification of two governed cross-insurer replications.

This read-only certifier verifies authoritative artifacts and their publication
receipts, then records what was reused and any reviewed generic capability
extension. It does not publish, mutate, or evaluate policy rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


class CrossInsurerReplicationCertificationError(ValueError):
    """Raised when the replication evidence is incomplete or inconsistent."""


@dataclass(frozen=True)
class CrossInsurerReplicationCertificationResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CrossInsurerReplicationCertificationError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CrossInsurerReplicationCertificationError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CrossInsurerReplicationCertificationError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise CrossInsurerReplicationCertificationError(
            f"{label} must be a safe repository-relative path"
        )
    return path.as_posix()


def _load_json(root: Path, relative_path: str, label: str) -> tuple[Mapping[str, Any], str]:
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise CrossInsurerReplicationCertificationError(
            f"{label} must remain under repository_root"
        ) from exc
    if not target.is_file():
        raise FileNotFoundError(f"{label} was not found: {relative_path}")
    raw = target.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CrossInsurerReplicationCertificationError(
            f"{label} is not valid UTF-8 JSON"
        ) from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


class CrossInsurerReplicationCertification:
    """Certifies a narrow, read-only cross-insurer replication milestone."""

    def certify_from_spec_file(
        self, *, spec_path: str | Path, repository_root: str | Path
    ) -> CrossInsurerReplicationCertificationResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Certification specification was not found: {path}")
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CrossInsurerReplicationCertificationError(
                "Certification specification is not valid JSON"
            ) from exc
        return self.certify(spec=_mapping(parsed, "certification_spec"), repository_root=repository_root)

    def certify(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        certified_at: str | None = None,
    ) -> CrossInsurerReplicationCertificationResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")
        if spec.get("schema_version") != "1.0":
            raise CrossInsurerReplicationCertificationError(
                "certification_spec.schema_version must be 1.0"
            )
        if spec.get("certification_type") != "cross_insurer_replication_certification_v1":
            raise CrossInsurerReplicationCertificationError(
                "certification_spec.certification_type is invalid"
            )
        if spec.get("reviewed_by_human") is not True:
            raise CrossInsurerReplicationCertificationError(
                "certification_spec.reviewed_by_human must be true"
            )

        reused_capabilities = [
            _text(item, "reused_capabilities[]")
            for item in _items(spec.get("reused_capabilities"), "reused_capabilities")
        ]
        if not reused_capabilities or len(reused_capabilities) != len(set(reused_capabilities)):
            raise CrossInsurerReplicationCertificationError(
                "reused_capabilities must be non-empty and unique"
            )

        extensions = _items(spec.get("controlled_extensions"), "controlled_extensions")
        replications = _items(spec.get("replications"), "replications")
        if len(replications) < 2:
            raise CrossInsurerReplicationCertificationError(
                "at least two replications are required"
            )

        insurer_product_pairs: set[tuple[str, str]] = set()
        certified_replications: list[dict[str, Any]] = []
        for index, raw in enumerate(replications):
            item = _mapping(raw, f"replications[{index}]")
            insurer_id = _text(item.get("insurer_id"), "replication.insurer_id")
            product_id = _text(item.get("product_id"), "replication.product_id")
            pair = (insurer_id, product_id)
            if pair in insurer_product_pairs:
                raise CrossInsurerReplicationCertificationError(
                    "replications must use distinct insurer/product pairs"
                )
            insurer_product_pairs.add(pair)

            artifact_path = _safe_relative_path(item.get("authoritative_artifact_path"), "authoritative_artifact_path")
            receipt_path = _safe_relative_path(item.get("publication_receipt_path"), "publication_receipt_path")
            artifact, artifact_sha = _load_json(root, artifact_path, "authoritative_artifact")
            receipt, _ = _load_json(root, receipt_path, "publication_receipt")

            if artifact.get("artifact_type") != "canonical_authoritative_generic_legal_assertions_v1":
                raise CrossInsurerReplicationCertificationError(
                    f"authoritative artifact type is invalid for {insurer_id}:{product_id}"
                )
            if artifact.get("publication_status") != "authoritative":
                raise CrossInsurerReplicationCertificationError(
                    f"authoritative artifact is not authoritative for {insurer_id}:{product_id}"
                )
            if receipt.get("receipt_type") != "canonical_authoritative_publication_receipt_v1":
                raise CrossInsurerReplicationCertificationError(
                    f"publication receipt type is invalid for {insurer_id}:{product_id}"
                )
            if receipt.get("publication_status") != "authoritative":
                raise CrossInsurerReplicationCertificationError(
                    f"publication receipt is not authoritative for {insurer_id}:{product_id}"
                )
            if receipt.get("artifact_sha256") != artifact_sha:
                raise CrossInsurerReplicationCertificationError(
                    f"receipt artifact hash mismatch for {insurer_id}:{product_id}"
                )
            expected_version = _text(item.get("product_version_id"), "replication.product_version_id")
            if artifact.get("product_version_id") != expected_version or receipt.get("product_version_id") != expected_version:
                raise CrossInsurerReplicationCertificationError(
                    f"product version mismatch for {insurer_id}:{product_id}"
                )

            assertions = _items(artifact.get("assertions"), "authoritative_artifact.assertions")
            expected_rule_types = {
                _text(rule_type, "expected_rule_types[]")
                for rule_type in _items(item.get("expected_rule_types"), "expected_rule_types")
            }
            # Build rule types explicitly so malformed payloads receive a useful error.
            actual_rule_types: set[str] = set()
            assertion_ids: list[str] = []
            for raw_assertion in assertions:
                assertion = _mapping(raw_assertion, "authoritative_assertion")
                if assertion.get("publication_status") != "authoritative":
                    raise CrossInsurerReplicationCertificationError(
                        f"non-authoritative assertion found for {insurer_id}:{product_id}"
                    )
                payload = _mapping(assertion.get("payload"), "assertion.payload")
                actual_rule_types.add(_text(payload.get("rule_type"), "assertion.payload.rule_type"))
                assertion_ids.append(_text(assertion.get("assertion_id"), "assertion.assertion_id"))
            if actual_rule_types != expected_rule_types:
                raise CrossInsurerReplicationCertificationError(
                    f"rule type mismatch for {insurer_id}:{product_id}"
                )
            receipt_ids = _items(receipt.get("published_assertion_ids"), "publication_receipt.published_assertion_ids")
            if sorted(receipt_ids) != sorted(assertion_ids):
                raise CrossInsurerReplicationCertificationError(
                    f"receipt assertion ids do not match artifact for {insurer_id}:{product_id}"
                )

            certified_replications.append({
                "insurer_id": insurer_id,
                "product_id": product_id,
                "product_version_id": expected_version,
                "authoritative_artifact_path": artifact_path,
                "authoritative_artifact_sha256": artifact_sha,
                "publication_receipt_path": receipt_path,
                "published_assertion_ids": assertion_ids,
                "rule_types": sorted(actual_rule_types),
                "receipt_integrity": "verified",
            })

        normalized_extensions: list[dict[str, str]] = []
        for index, raw in enumerate(extensions):
            item = _mapping(raw, f"controlled_extensions[{index}]")
            normalized_extensions.append({
                "capability": _text(item.get("capability"), "controlled_extension.capability"),
                "change": _text(item.get("change"), "controlled_extension.change"),
                "safeguard_impact": _text(item.get("safeguard_impact"), "controlled_extension.safeguard_impact"),
            })

        return CrossInsurerReplicationCertificationResult(
            manifest={
                "schema_version": "1.0",
                "certification_type": "cross_insurer_replication_certification_v1",
                "certification_status": "cross_insurer_replication_certified",
                "certified_at": certified_at or datetime.now(timezone.utc).isoformat(),
                "replications": certified_replications,
                "reused_capabilities": reused_capabilities,
                "controlled_extensions": normalized_extensions,
                "conclusion": _text(spec.get("conclusion"), "conclusion"),
                "out_of_scope": [
                    _text(item, "out_of_scope[]")
                    for item in _items(spec.get("out_of_scope"), "out_of_scope")
                ],
                "guardrails": [
                    "Certification is read-only and does not create, change, or republish assertions.",
                    "Every replication requires an authoritative artifact and a receipt whose artifact hash matches exact persisted artifact bytes.",
                    "Only the expected rule types for each reviewed replication are certified.",
                    "Certification does not certify broad product coverage or personalized rule execution.",
                ],
            }
        )

    def write_output(
        self,
        result: CrossInsurerReplicationCertificationResult,
        *,
        repository_root: str | Path,
        output_path: str | Path,
    ) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise CrossInsurerReplicationCertificationError(
                "output_path must remain under repository_root"
            ) from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
