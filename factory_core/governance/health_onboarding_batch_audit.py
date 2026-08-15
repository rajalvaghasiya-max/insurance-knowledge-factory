"""Read-only, specification-driven audit for Phase-2A Health onboarding batches.

The audit measures governed-artifact availability and optional review-risk workload
without inferring product facts, mutating knowledge, or embedding product identity
in production code. Product identities and artifact paths are supplied by a batch
specification.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping


class HealthOnboardingBatchAuditError(ValueError):
    """Raised when a batch-audit specification or governed artifact is unsafe."""


@dataclass(frozen=True)
class HealthOnboardingBatchAuditResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise HealthOnboardingBatchAuditError(f"{label} must be an object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise HealthOnboardingBatchAuditError(f"{label} must be a list")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HealthOnboardingBatchAuditError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    if (
        Path(raw).is_absolute()
        or PurePosixPath(raw).is_absolute()
        or PureWindowsPath(raw).is_absolute()
        or raw.startswith("\\\\")
        or ":" in raw[:3]
        or ".." in PurePosixPath(raw).parts
        or ".." in PureWindowsPath(raw).parts
    ):
        raise HealthOnboardingBatchAuditError(f"{label} must be a safe repository-relative path")
    return PurePosixPath(raw.replace("\\", "/")).as_posix()


def _resolve(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HealthOnboardingBatchAuditError("artifact path must remain under repository_root") from exc
    return candidate


def _load_json_if_present(root: Path, relative: str) -> tuple[Mapping[str, Any] | None, str | None]:
    path = _resolve(root, relative)
    if not path.is_file():
        return None, None
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HealthOnboardingBatchAuditError(f"governed artifact is not valid UTF-8 JSON: {relative}") from exc
    return _mapping(parsed, relative), sha256(raw).hexdigest()


class HealthOnboardingBatchAudit:
    SCHEMA_VERSION = "1.0"
    AUDIT_TYPE = "phase_2a_health_onboarding_batch_audit_v1"
    REVIEW_ROUTING_REQUIRED = "required_when_review_input_exists"
    REVIEW_ROUTING_NOT_APPLICABLE = "not_applicable_no_review_input"
    _ALLOWED_REVIEW_ROUTING_APPLICABILITY = {
        REVIEW_ROUTING_REQUIRED,
        REVIEW_ROUTING_NOT_APPLICABLE,
    }
    _ALLOWED_ARTIFACT_KEYS = (
        "registration",
        "classification",
        "product_identity",
        "identity_resolution",
        "currentness_evidence",
        "review_risk_routing",
    )

    @classmethod
    def audit_from_spec_file(
        cls, *, spec_path: str | Path, repository_root: str | Path
    ) -> HealthOnboardingBatchAuditResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"batch audit specification was not found: {path}")
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HealthOnboardingBatchAuditError("batch audit specification is not valid UTF-8 JSON") from exc
        return cls.audit(spec=_mapping(parsed, "batch_audit_spec"), repository_root=repository_root)

    @classmethod
    def audit(cls, *, spec: Mapping[str, Any], repository_root: str | Path) -> HealthOnboardingBatchAuditResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")
        if spec.get("schema_version") != cls.SCHEMA_VERSION:
            raise HealthOnboardingBatchAuditError("schema_version must be 1.0")
        if spec.get("audit_type") != cls.AUDIT_TYPE:
            raise HealthOnboardingBatchAuditError("audit_type is invalid")

        products = _list(spec.get("products"), "products")
        if not products:
            raise HealthOnboardingBatchAuditError("products must be non-empty")

        seen_entities: set[str] = set()
        rows: list[dict[str, Any]] = []
        total_missing = 0
        total_routed_groups = 0
        routing_not_applicable_count = 0
        tier_totals = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for index, raw_product in enumerate(products):
            product = _mapping(raw_product, f"products[{index}]")
            entity_id = _text(product.get("entity_id"), f"products[{index}].entity_id")
            if entity_id in seen_entities:
                raise HealthOnboardingBatchAuditError("product entity_id values must be unique")
            seen_entities.add(entity_id)

            routing_applicability = _text(
                product.get("review_routing_applicability", cls.REVIEW_ROUTING_REQUIRED),
                f"products[{index}].review_routing_applicability",
            )
            if routing_applicability not in cls._ALLOWED_REVIEW_ROUTING_APPLICABILITY:
                raise HealthOnboardingBatchAuditError("unsupported review_routing_applicability")

            artifacts = _mapping(product.get("artifacts", {}), f"products[{index}].artifacts")
            unknown_keys = sorted(set(artifacts) - set(cls._ALLOWED_ARTIFACT_KEYS))
            if unknown_keys:
                raise HealthOnboardingBatchAuditError(
                    "unsupported artifact key(s): " + ", ".join(unknown_keys)
                )
            if (
                routing_applicability == cls.REVIEW_ROUTING_NOT_APPLICABLE
                and artifacts.get("review_risk_routing") is not None
            ):
                raise HealthOnboardingBatchAuditError(
                    "review_risk_routing must not be declared when review routing is not applicable"
                )

            artifact_rows: dict[str, Any] = {}
            missing: list[str] = []
            routing_summary = None
            for key in cls._ALLOWED_ARTIFACT_KEYS:
                raw_path = artifacts.get(key)
                if key == "review_risk_routing" and routing_applicability == cls.REVIEW_ROUTING_NOT_APPLICABLE:
                    artifact_rows[key] = {
                        "status": cls.REVIEW_ROUTING_NOT_APPLICABLE,
                        "path": None,
                        "sha256": None,
                    }
                    routing_not_applicable_count += 1
                    continue
                if raw_path is None:
                    artifact_rows[key] = {"status": "not_declared", "path": None, "sha256": None}
                    missing.append(key)
                    continue
                relative = _safe_relative_path(raw_path, f"products[{index}].artifacts.{key}")
                document, digest = _load_json_if_present(root, relative)
                if document is None:
                    artifact_rows[key] = {"status": "declared_missing", "path": relative, "sha256": None}
                    missing.append(key)
                    continue
                artifact_rows[key] = {"status": "present", "path": relative, "sha256": digest}
                if key == "review_risk_routing":
                    routing_summary = cls._routing_summary(document)
                    total_routed_groups += routing_summary["routing_record_count"]
                    for tier, count in routing_summary["tier_counts"].items():
                        tier_totals[tier] += count

            total_missing += len(missing)
            rows.append({
                "entity_id": entity_id,
                "display_name": _text(product.get("display_name"), f"products[{index}].display_name"),
                "review_routing_applicability": routing_applicability,
                "artifacts": artifact_rows,
                "missing_or_undeclared_artifacts": missing,
                "artifact_completeness_status": "complete_for_declared_audit" if not missing else "incomplete_explicit",
                "review_risk_summary": routing_summary,
                "product_specific_production_code_change_required": False,
                "product_specific_code_guardrail": "audit_inputs_are_spec_driven_no_product_branching",
            })

        manifest = {
            "schema_version": cls.SCHEMA_VERSION,
            "audit_type": cls.AUDIT_TYPE,
            "audit_status": "batch_audited_read_only",
            "product_count": len(rows),
            "products": rows,
            "batch_summary": {
                "products_with_explicit_missing_artifacts": sum(
                    1 for row in rows if row["missing_or_undeclared_artifacts"]
                ),
                "missing_or_undeclared_artifact_count": total_missing,
                "review_routing_record_count": total_routed_groups,
                "review_routing_not_applicable_no_review_input_count": routing_not_applicable_count,
                "review_risk_tier_counts": tier_totals,
                "product_identity_bearing_production_code_changes": 0,
            },
            "guardrails": [
                "Batch audit is read-only and does not create or mutate product knowledge.",
                "Product identities and artifact paths are supplied only by the governed batch specification.",
                "Missing artifacts remain explicit and are never inferred as complete.",
                "Review-risk routing is required only when reviewer-ready input exists; absence of review input is recorded explicitly rather than converted into fake routing workload.",
                "Review-risk metrics are workload metadata only and do not adjudicate evidence or publish facts.",
                "The audit does not authorize product-specific production code.",
            ],
        }
        cls.validate(manifest)
        return HealthOnboardingBatchAuditResult(manifest=manifest)

    @classmethod
    def _routing_summary(cls, document: Mapping[str, Any]) -> dict[str, Any]:
        if document.get("routing_type") != "governed_review_risk_routing_v1":
            raise HealthOnboardingBatchAuditError("review_risk_routing artifact has unsupported routing_type")
        records = _list(document.get("routing_records"), "review_risk_routing.routing_records")
        if document.get("routing_record_count") != len(records):
            raise HealthOnboardingBatchAuditError("review_risk_routing count mismatch")
        workload = _mapping(document.get("workload_summary"), "review_risk_routing.workload_summary")
        tiers = _mapping(workload.get("tier_counts"), "review_risk_routing.workload_summary.tier_counts")
        normalized = {}
        for tier in ("critical", "high", "medium", "low"):
            value = tiers.get(tier, 0)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise HealthOnboardingBatchAuditError("review risk tier counts must be non-negative integers")
            normalized[tier] = value
        if sum(normalized.values()) != len(records):
            raise HealthOnboardingBatchAuditError("review risk tier counts must equal routing_record_count")
        return {"routing_record_count": len(records), "tier_counts": normalized}

    @classmethod
    def validate(cls, manifest: Mapping[str, Any]) -> None:
        document = _mapping(manifest, "audit_manifest")
        if document.get("schema_version") != cls.SCHEMA_VERSION:
            raise HealthOnboardingBatchAuditError("unsupported audit schema_version")
        if document.get("audit_type") != cls.AUDIT_TYPE:
            raise HealthOnboardingBatchAuditError("unsupported audit_type")
        if document.get("audit_status") != "batch_audited_read_only":
            raise HealthOnboardingBatchAuditError("audit_status must remain read-only")
        products = _list(document.get("products"), "products")
        if document.get("product_count") != len(products):
            raise HealthOnboardingBatchAuditError("product_count must equal products length")
        summary = _mapping(document.get("batch_summary"), "batch_summary")
        if summary.get("product_identity_bearing_production_code_changes") != 0:
            raise HealthOnboardingBatchAuditError("batch audit must not claim product-specific production-code changes")

    @classmethod
    def write_output(
        cls,
        result: HealthOnboardingBatchAuditResult,
        *,
        repository_root: str | Path,
        output_path: str | Path,
    ) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = _resolve(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target


__all__ = [
    "HealthOnboardingBatchAudit",
    "HealthOnboardingBatchAuditError",
    "HealthOnboardingBatchAuditResult",
]
