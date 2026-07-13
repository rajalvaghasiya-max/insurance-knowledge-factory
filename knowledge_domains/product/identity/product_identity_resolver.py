"""Evidence-backed Product Identity Resolution v1.

This resolver consumes product-scoped intelligence outputs. It does not infer
identity from generic webpages, category pages, filenames, or unlabelled codes.
A verified identity requires a format-valid UIN candidate with local provenance
from an approved product document and a matching product-scoped entity.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.uin_candidate_extractor import UinCandidateExtractor
from config.settings import BASE_DIR
from knowledge_domains.product.identity.product_identity_models import (
    IdentityResolutionStatus,
    ProductIdentityDecision,
)


IDENTITY_RESOLVER_VERSION = "1.0"
APPROVED_UIN_SOURCE_TYPES = {
    "policy_wording",
    "customer_information_sheet",
    "prospectus",
    "brochure",
}


class ProductIdentityResolver:
    """Resolves product identity from product intelligence outputs."""

    def resolve(
        self,
        intelligence: dict[str, Any],
        *,
        source_intelligence_file: str | None = None,
    ) -> ProductIdentityDecision:
        entity_id = str(intelligence.get("entity_id") or "")
        insurer_id, product_slug = self._split_entity_id(entity_id)
        metadata = intelligence.get("metadata") or {}
        product_name = self._clean_text(metadata.get("product_name"))
        raw_uin = self._clean_text(metadata.get("uin"))
        candidate = metadata.get("uin_candidate")

        reasons: list[str] = []
        evidence: list[dict[str, Any]] = []

        if not entity_id or not insurer_id or not product_slug:
            reasons.append("missing_or_invalid_entity_id")
        if not product_name:
            reasons.append("missing_product_name")
        if not raw_uin:
            reasons.append("missing_uin")

        if raw_uin and not UinCandidateExtractor.is_format_valid(raw_uin):
            reasons.append("invalid_uin_format")

        if isinstance(candidate, dict):
            candidate_uin = self._clean_text(candidate.get("uin"))
            if candidate_uin != raw_uin:
                reasons.append("uin_candidate_does_not_match_metadata_uin")
            elif candidate.get("candidate_status") != "format_valid_candidate":
                reasons.append("uin_candidate_not_format_valid")
            else:
                source = candidate.get("source")
                if not isinstance(source, dict):
                    reasons.append("uin_candidate_missing_source_provenance")
                elif source.get("source_type") not in APPROVED_UIN_SOURCE_TYPES:
                    reasons.append("uin_candidate_source_not_approved")
                elif not source.get("source_file") or not source.get("page_number"):
                    reasons.append("uin_candidate_source_incomplete")
                else:
                    evidence.append(dict(candidate))
        elif raw_uin:
            reasons.append("legacy_uin_without_candidate_provenance")

        hard_failures = {
            "missing_or_invalid_entity_id",
            "missing_product_name",
            "missing_uin",
            "invalid_uin_format",
        }
        if any(reason in hard_failures for reason in reasons):
            status = IdentityResolutionStatus.UNRESOLVED
            method = None
        elif evidence and not reasons:
            status = IdentityResolutionStatus.VERIFIED
            method = "product_scoped_document_uin_candidate"
        elif raw_uin:
            status = IdentityResolutionStatus.PROBABLE
            method = "uin_present_but_provenance_incomplete"
        else:
            status = IdentityResolutionStatus.UNRESOLVED
            method = None

        return ProductIdentityDecision(
            entity_id=entity_id,
            insurer_id=insurer_id,
            product_slug=product_slug,
            product_name=product_name,
            uin=raw_uin,
            status=status,
            resolution_method=method,
            reasons=tuple(reasons),
            evidence=tuple(evidence),
            source_intelligence_file=source_intelligence_file,
        )

    @staticmethod
    def _split_entity_id(entity_id: str) -> tuple[str, str]:
        if entity_id.count(":") != 1:
            return "", ""
        insurer_id, product_slug = entity_id.split(":", 1)
        if not insurer_id.strip() or not product_slug.strip():
            return "", ""
        return insurer_id.strip(), product_slug.strip()

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None


class ProductIdentityRegistryBuilder:
    """Builds the canonical verified Product Identity Registry from decisions."""

    def __init__(
        self,
        *,
        base_dir: Path | None = None,
        resolver: ProductIdentityResolver | None = None,
    ) -> None:
        self.base_dir = base_dir or BASE_DIR
        self.resolver = resolver or ProductIdentityResolver()

    @property
    def intelligence_root(self) -> Path:
        return self.base_dir / "knowledge" / "health"

    @property
    def registry_path(self) -> Path:
        return self.base_dir / "registry" / "product_identity_registry.json"

    @property
    def report_path(self) -> Path:
        return self.base_dir / "reports" / "product_identity_resolution_report.json"

    def build(self) -> dict[str, Any]:
        decisions = self._load_decisions()
        decisions = self._mark_conflicts(decisions)
        identities = self._build_verified_identities(decisions)

        registry = {
            "schema_version": "1.0",
            "resolver_version": IDENTITY_RESOLVER_VERSION,
            "generated_at": self._utc_now(),
            "identity_count": len(identities),
            "identities": identities,
        }
        report = {
            "resolver_version": IDENTITY_RESOLVER_VERSION,
            "generated_at": self._utc_now(),
            "scanned_intelligence_files": len(decisions),
            "status_counts": self._status_counts(decisions),
            "decisions": [decision.to_dict() for decision in decisions],
            "registry_output": self._relative_path(self.registry_path),
        }

        self._write_json(self.registry_path, registry)
        self._write_json(self.report_path, report)

        return {
            "registry": registry,
            "report": report,
            "registry_path": self.registry_path,
            "report_path": self.report_path,
        }

    def _load_decisions(self) -> list[ProductIdentityDecision]:
        decisions: list[ProductIdentityDecision] = []
        if not self.intelligence_root.exists():
            return decisions

        for path in sorted(self.intelligence_root.glob("*/*/intelligence/product_intelligence.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid product intelligence JSON: {path}") from exc
            decisions.append(
                self.resolver.resolve(
                    payload,
                    source_intelligence_file=self._relative_path(path),
                )
            )
        return decisions

    def _mark_conflicts(
        self,
        decisions: list[ProductIdentityDecision],
    ) -> list[ProductIdentityDecision]:
        names_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
        for decision in decisions:
            if decision.status is IdentityResolutionStatus.VERIFIED and decision.uin:
                names_by_key[(decision.insurer_id, decision.uin)].add(
                    self._normalize_name(decision.product_name or "")
                )

        results: list[ProductIdentityDecision] = []
        for decision in decisions:
            key = (decision.insurer_id, decision.uin or "")
            conflicting_names = names_by_key.get(key, set())
            if (
                decision.status is IdentityResolutionStatus.VERIFIED
                and len(conflicting_names) > 1
            ):
                reasons = tuple((*decision.reasons, "conflicting_product_names_for_same_insurer_uin"))
                results.append(
                    ProductIdentityDecision(
                        entity_id=decision.entity_id,
                        insurer_id=decision.insurer_id,
                        product_slug=decision.product_slug,
                        product_name=decision.product_name,
                        uin=decision.uin,
                        status=IdentityResolutionStatus.AMBIGUOUS,
                        resolution_method=None,
                        reasons=reasons,
                        evidence=decision.evidence,
                        source_intelligence_file=decision.source_intelligence_file,
                    )
                )
            else:
                results.append(decision)
        return results

    def _build_verified_identities(
        self,
        decisions: list[ProductIdentityDecision],
    ) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], list[ProductIdentityDecision]] = defaultdict(list)
        for decision in decisions:
            if decision.status is IdentityResolutionStatus.VERIFIED and decision.uin:
                grouped[(decision.insurer_id, decision.uin)].append(decision)

        identities: list[dict[str, Any]] = []
        for (insurer_id, uin), members in sorted(grouped.items()):
            first = members[0]
            product_names = sorted({member.product_name for member in members if member.product_name})
            identities.append(
                {
                    "product_identity_id": self._identity_id(insurer_id, uin),
                    "insurer_id": insurer_id,
                    "canonical_product_name": product_names[0] if product_names else None,
                    "aliases": product_names[1:],
                    "product_variant": None,
                    "uin": uin,
                    "lifecycle_status": "unknown",
                    "resolution_status": "verified",
                    "resolution_method": "product_scoped_document_uin_candidate",
                    "entity_ids": sorted({member.entity_id for member in members}),
                    "evidence": [evidence for member in members for evidence in member.evidence],
                }
            )
        return identities

    @staticmethod
    def _identity_id(insurer_id: str, uin: str) -> str:
        digest = hashlib.sha256(f"{insurer_id}:{uin}".encode("utf-8")).hexdigest()[:12]
        return f"pid_{digest}"

    @staticmethod
    def _normalize_name(name: str) -> str:
        return " ".join(name.lower().split())

    @staticmethod
    def _status_counts(decisions: list[ProductIdentityDecision]) -> dict[str, int]:
        counts = {status.value: 0 for status in IdentityResolutionStatus}
        for decision in decisions:
            counts[decision.status.value] += 1
        return counts

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            return str(path)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
