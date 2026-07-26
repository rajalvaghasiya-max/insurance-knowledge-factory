from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


class EvidenceRouter:
    """
    Evidence Router v0.5

    Purpose:
        Build an evidence-first routing plan for a product/entity + field.

    Improvements over v0.3:
        - Evidence records with stable evidence_id and document_id.
        - Field-aware keyword scoring.
        - Explainable routing_score and scoring_breakdown.
        - Duplicate grouping by logical document key.
        - Backward-compatible candidates list for existing runners.
        - Separate evidence_bundles for parser/extractor consumption.
    """

    VERSION = "0.5"

    SUPPORTED_SUFFIXES = {".json", ".txt", ".md"}
    MAX_FILE_SIZE_BYTES = 5_000_000
    READ_LIMIT = 25_000

    # Evidence Router must only route source evidence, not downstream outputs.
    # These folders/files are produced by later agents and must never become evidence.
    EXCLUDED_EVIDENCE_PATH_PARTS = [
        "/intelligence/",
        "/coverage/",
        "/coverage_audits/",
        "/recommendations/",
        "/explanations/",
        "/comparisons/",
        "/portfolio/",
        "/validation/",
        "/validation_reports/",
        "/validations/",
        "/identity/",
        "/document_acquisition/",
        "/routing_plans/",
        "/extracted_facts/",
        "/normalized/",
        "/ontology/",
        "/facts/",
    ]

    EXCLUDED_EVIDENCE_FILE_PATTERNS = [
        "parse_report",
        "download_report",
        "coverage_report",
        "coverage_audit",
        "validation_report",
        "expected",
        "recommendation",
        "comparison",
        "explanation",
        "portfolio",
        "identity_report",
    ]

    RAW_EVIDENCE_ROLES = {
        "policy_wording": "legal_authority",
        "customer_information_sheet": "regulatory_summary",
        "cis": "regulatory_summary",
        "prospectus": "product_disclosure",
        "brochure": "marketing_disclosure",
        "webpage": "published_web_source",
    }

    FIELD_SOURCE_PRIORITY = {
        "ped_waiting_period": [
            "policy_wording",
            "customer_information_sheet",
            "cis",
            "prospectus",
            "brochure",
            "webpage",
        ],
        "initial_waiting_period": [
            "policy_wording",
            "customer_information_sheet",
            "cis",
            "prospectus",
            "brochure",
            "webpage",
        ],
        "room_rent": [
            "policy_wording",
            "customer_information_sheet",
            "cis",
            "prospectus",
            "brochure",
            "webpage",
        ],
        "room_rent_limit": [
            "policy_wording",
            "customer_information_sheet",
            "cis",
            "prospectus",
            "brochure",
            "webpage",
        ],
        "copay": [
            "policy_wording",
            "customer_information_sheet",
            "cis",
            "prospectus",
            "brochure",
            "webpage",
        ],
        "specific_disease_waiting_period": [
            "policy_wording",
            "customer_information_sheet",
            "cis",
            "prospectus",
            "brochure",
        ],
        "restoration_benefit": [
            "policy_wording",
            "brochure",
            "customer_information_sheet",
            "cis",
            "webpage",
        ],
    }

    FIELD_KEYWORDS = {
        "copay": [
            "co-pay",
            "co pay",
            "copay",
            "co-payment",
            "co payment",
            "deductible",
            "share of claim",
            "percentage of admissible claim",
        ],
        "room_rent": [
            "room rent",
            "room category",
            "single private room",
            "private room",
            "icu",
            "intensive care",
            "boarding",
            "nursing",
        ],
        "room_rent_limit": [
            "room rent",
            "room category",
            "single private room",
            "private room",
            "icu",
            "intensive care",
            "boarding",
            "nursing",
        ],
        "ped_waiting_period": [
            "pre-existing disease",
            "pre existing disease",
            "ped",
            "waiting period",
            "pre-existing condition",
            "pre existing condition",
        ],
        "initial_waiting_period": [
            "initial waiting period",
            "initial wait",
            "first 30 days",
            "first 60 days",
            "first 90 days",
            "accidental injuries",
            "accidental hospitalization",
            "excluding accidental hospitalization",
        ],
        "specific_disease_waiting_period": [
            "specific disease",
            "listed disease",
            "waiting period",
            "cataract",
            "hernia",
            "joint replacement",
            "knee replacement",
        ],
        "restoration_benefit": [
            "restoration",
            "restore",
            "reinstatement",
            "reload",
            "sum insured restoration",
            "automatic restoration",
        ],
    }

    SOURCE_TYPE_HINTS = {
        "policy_wording": [
            "policy_wording",
            "policy-wording",
            "policy wording",
            "policy_document",
            "policy-document",
            "policy document",
            "wording",
        ],
        "customer_information_sheet": [
            "customer_information_sheet",
            "customer-information-sheet",
            "customer information sheet",
            "customerinformation",
            "cis",
        ],
        "cis": [
            "cis",
            "customer_information_sheet",
            "customer-information-sheet",
        ],
        "prospectus": ["prospectus"],
        "brochure": ["brochure"],
        "webpage": [
            "html_sections",
            "html-sections",
            "webpage",
            "page",
        ],
    }

    BLOCKED_CONTEXTS_BY_ENTITY = {
        "aditya_birla_health:activ_one": [
            "lifeinsurance",
            "life-insurance",
            "motorinsurance",
            "motor-insurance",
            "pensionfund",
            "pension",
            "travelinsurance",
            "travel-insurance",
            "overseas-travel",
            "abc-of-calculators",
            "calculator",
            "critical-illness-insurance",
            "cancer-insurance",
            "corporate-health-insurance",
            "faqs",
        ]
    }

    PRODUCT_ALIASES_BY_ENTITY = {
        "aditya_birla_health:activ_one": [
            "activ-one",
            "activ_one",
            "activ one",
            "activone",
            "active-one",
            "active_one",
            "active one",
            "activeone",
        ]
    }

    RELATED_PRODUCT_ALIASES_BY_ENTITY = {
        "aditya_birla_health:activ_one": [
            "activonemax",
            "activ-one-max",
            "activone max",
            "maxplus",
            "max plus",
            "activonemaxplus",
            "activ-one-max-plus",
            "activonevytl",
            "activ-one-vytl",
        ]
    }

    INSURER_ALIASES_BY_ENTITY = {
        "aditya_birla_health:activ_one": [
            "aditya_birla_health",
            "aditya birla health",
            "adityabirlacapital.com/healthinsurance",
            "healthinsurance",
        ]
    }

    def resolve_search_plan(
        self,
        *,
        entity_id: str,
        field: str,
        base_roots: list[str] | None = None,
    ) -> dict[str, Any]:
        if base_roots is None:
            base_roots = ["knowledge", "parsed", "archive"]

        priority_sources = self.get_priority_sources(field)
        rejected_counts: dict[str, int] = {
            "not_entity_match": 0,
            "blocked_context": 0,
            "unsupported_source_type": 0,
            "excluded_derived_artifact": 0,
            "duplicate_lower_score": 0,
        }

        evidence_records: list[dict[str, Any]] = []

        for root_str in base_roots:
            root = BASE_DIR / root_str
            if not root.exists():
                continue

            for path in self.iter_supported_files(root):
                if self.is_excluded_derived_artifact(path):
                    rejected_counts["excluded_derived_artifact"] = rejected_counts.get("excluded_derived_artifact", 0) + 1
                    continue

                raw_text = self.read_small_text(path)
                match_result = self.path_matches_entity(path, entity_id, raw_text)

                if not match_result["matched"]:
                    reason = match_result["reason"]
                    rejected_counts[reason] = rejected_counts.get(reason, 0) + 1
                    continue

                source_type = self.classify_source_type(path, raw_text)
                if source_type not in priority_sources:
                    rejected_counts["unsupported_source_type"] += 1
                    continue

                field_hits = self.find_field_hits(field, f"{path}\n{raw_text}")
                record = self.build_evidence_record(
                    path=path,
                    entity_id=entity_id,
                    field=field,
                    source_type=source_type,
                    priority_sources=priority_sources,
                    match_result=match_result,
                    field_hits=field_hits,
                    raw_text=raw_text,
                )
                evidence_records.append(record)

        deduped_records = self.deduplicate_evidence(evidence_records, rejected_counts)
        deduped_records = sorted(
            deduped_records,
            key=lambda item: (-item["routing_score"], item["priority"], item["relative_path"]),
        )

        evidence_bundles = self.build_evidence_bundles(deduped_records)

        # Backward-compatible alias for existing downstream code.
        candidates = deduped_records

        return {
            "entity_id": entity_id,
            "field": field,
            "router_version": self.VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "priority_sources": priority_sources,
            "candidate_count": len(candidates),
            "evidence_count": len(deduped_records),
            "bundle_count": len(evidence_bundles),
            "rejected_counts": rejected_counts,
            "candidates": candidates,
            "evidence_records": deduped_records,
            "evidence_bundles": evidence_bundles,
        }

    def get_priority_sources(self, field: str) -> list[str]:
        return self.FIELD_SOURCE_PRIORITY.get(
            field,
            ["policy_wording", "customer_information_sheet", "brochure", "webpage"],
        )

    def iter_supported_files(self, root: Path):
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
                continue

            lower = str(path).lower().replace("\\", "/")
            if "/.venv/" in lower or "\\.venv\\" in lower:
                continue


            try:
                if path.stat().st_size > self.MAX_FILE_SIZE_BYTES:
                    continue
            except OSError:
                continue

            yield path

    def build_evidence_record(
        self,
        *,
        path: Path,
        entity_id: str,
        field: str,
        source_type: str,
        priority_sources: list[str],
        match_result: dict[str, Any],
        field_hits: list[str],
        raw_text: str,
    ) -> dict[str, Any]:
        relative_path = str(path.relative_to(BASE_DIR)).replace("\\", "/")
        document_hash = self.file_hash(path)
        logical_document_key = self.logical_document_key(path, source_type)
        document_id = self.stable_id("doc", logical_document_key)
        evidence_id = self.stable_id("ev", f"{entity_id}|{field}|{relative_path}|{document_hash[:16]}")
        priority = priority_sources.index(source_type)

        score, breakdown = self.score_evidence(
            source_type=source_type,
            priority=priority,
            match_reason=match_result["reason"],
            field_hits=field_hits,
            raw_text=raw_text,
        )

        return {
            "evidence_id": evidence_id,
            "document_id": document_id,
            "entity_id": entity_id,
            "field": field,
            "path": str(path),
            "relative_path": relative_path,
            "source_type": source_type,
            "document_type": source_type,
            "artifact_type": "raw_evidence",
            "evidence_role": self.RAW_EVIDENCE_ROLES.get(source_type, "source_evidence"),
            "priority": priority,
            "routing_score": score,
            "scoring_breakdown": breakdown,
            "match_reason": match_result["reason"],
            "matched_aliases": match_result.get("matched_aliases", []),
            "field_hits": field_hits,
            "document_hash": document_hash,
            "logical_document_key": logical_document_key,
            "file_size_bytes": self.safe_file_size(path),
            "modified_at": self.safe_modified_at(path),
            "selected_reasons": self.selected_reasons(source_type, match_result, field_hits, breakdown),
            "page": None,
            "section": None,
            "confidence": self.routing_confidence(score),
            "status": "candidate",
        }

    def score_evidence(
        self,
        *,
        source_type: str,
        priority: int,
        match_reason: str,
        field_hits: list[str],
        raw_text: str,
    ) -> tuple[int, dict[str, int]]:
        breakdown: dict[str, int] = {}

        if match_reason == "strong_product_match":
            breakdown["product_match"] = 50
        elif match_reason == "insurer_match":
            breakdown["insurer_match"] = 20
        else:
            breakdown["entity_match"] = 10

        breakdown["source_priority"] = max(0, 35 - (priority * 6))

        if field_hits:
            # Cap keyword boost so repeated mentions do not dominate source quality.
            breakdown["field_keyword_match"] = min(25, 8 + len(field_hits) * 4)
        else:
            breakdown["field_keyword_match"] = 0

        if source_type == "policy_wording":
            breakdown["legal_source_bonus"] = 12
        elif source_type in {"customer_information_sheet", "cis"}:
            breakdown["summary_source_bonus"] = 8
        else:
            breakdown["source_bonus"] = 0

        if self.looks_like_metadata(raw_text):
            breakdown["metadata_penalty"] = -4

        score = sum(breakdown.values())
        return score, breakdown

    def routing_confidence(self, score: int) -> float:
        if score >= 90:
            return 0.95
        if score >= 75:
            return 0.88
        if score >= 60:
            return 0.78
        if score >= 45:
            return 0.65
        return 0.50

    def deduplicate_evidence(
        self,
        records: list[dict[str, Any]],
        rejected_counts: dict[str, int],
    ) -> list[dict[str, Any]]:
        best_by_key: dict[str, dict[str, Any]] = {}

        for record in records:
            key = record["logical_document_key"]
            existing = best_by_key.get(key)
            if existing is None:
                best_by_key[key] = record
                continue

            current_rank = (record["routing_score"], -record["priority"], record["file_size_bytes"])
            existing_rank = (existing["routing_score"], -existing["priority"], existing["file_size_bytes"])

            if current_rank > existing_rank:
                record["duplicate_of"] = None
                existing["duplicate_of"] = record["evidence_id"]
                best_by_key[key] = record
            else:
                record["duplicate_of"] = existing["evidence_id"]

            rejected_counts["duplicate_lower_score"] = rejected_counts.get("duplicate_lower_score", 0) + 1

        return list(best_by_key.values())

    def build_evidence_bundles(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bundles: dict[str, dict[str, Any]] = {}

        for record in records:
            document_id = record["document_id"]
            if document_id not in bundles:
                bundles[document_id] = {
                    "bundle_id": self.stable_id("bundle", document_id),
                    "document_id": document_id,
                    "entity_id": record["entity_id"],
                    "field": record["field"],
                    "source_type": record["source_type"],
                    "best_evidence_id": record["evidence_id"],
                    "best_relative_path": record["relative_path"],
                    "best_routing_score": record["routing_score"],
                    "representations": [],
                }

            bundles[document_id]["representations"].append(
                {
                    "evidence_id": record["evidence_id"],
                    "relative_path": record["relative_path"],
                    "source_type": record["source_type"],
                    "routing_score": record["routing_score"],
                    "document_hash": record["document_hash"],
                }
            )

        return sorted(
            bundles.values(),
            key=lambda item: (-item["best_routing_score"], item["best_relative_path"]),
        )

    def is_excluded_derived_artifact(self, path: Path) -> bool:
        relative = str(path.relative_to(BASE_DIR)).lower().replace("\\", "/")
        wrapped = f"/{relative}"

        for part in self.EXCLUDED_EVIDENCE_PATH_PARTS:
            if part in wrapped:
                return True

        stem = path.stem.lower().replace("-", "_")
        for pattern in self.EXCLUDED_EVIDENCE_FILE_PATTERNS:
            if pattern in stem:
                return True

        return False

    def selected_reasons(
        self,
        source_type: str,
        match_result: dict[str, Any],
        field_hits: list[str],
        breakdown: dict[str, int],
    ) -> list[str]:
        reasons: list[str] = []

        if match_result.get("reason") == "strong_product_match":
            reasons.append("Product matched using explicit product alias")
        elif match_result.get("reason") == "insurer_match":
            reasons.append("Insurer matched")

        role = self.RAW_EVIDENCE_ROLES.get(source_type)
        if role == "legal_authority":
            reasons.append("Highest legal authority source")
        elif role == "regulatory_summary":
            reasons.append("Regulatory summary source")
        elif role == "product_disclosure":
            reasons.append("Product disclosure source")
        elif role == "marketing_disclosure":
            reasons.append("Marketing disclosure source")
        elif role == "published_web_source":
            reasons.append("Published product webpage or webpage metadata")

        if field_hits:
            reasons.append("Contains field keywords: " + ", ".join(field_hits[:5]))

        if breakdown.get("metadata_penalty"):
            reasons.append("Metadata-like source; kept only as lower authority supporting evidence")

        return reasons

    def classify_source_type(self, path: Path, raw_text: str | None = None) -> str:
        text = str(path).lower().replace("\\", "/").replace("_", "-")

        if "html-sections" in text or "html_sections" in text:
            return "webpage"

        for source_type, hints in self.SOURCE_TYPE_HINTS.items():
            for hint in hints:
                hint_l = hint.lower().replace("_", "-")
                if hint_l in text:
                    return source_type

        raw = raw_text if raw_text is not None else self.read_small_text(path)
        raw = raw.lower().replace("_", "-")

        if "policy wording" in raw or "policy-wording" in raw or "policy document" in raw:
            return "policy_wording"
        if "customer information sheet" in raw or "customer-information-sheet" in raw or " cis " in f" {raw} ":
            return "customer_information_sheet"
        if "brochure" in raw:
            return "brochure"
        if "prospectus" in raw:
            return "prospectus"

        return "webpage"

    def path_matches_entity(self, path: Path, entity_id: str, raw_text: str | None = None) -> dict[str, Any]:
        entity_id_l = entity_id.lower()
        path_text = str(path).lower().replace("\\", "/").replace("_", "-")
        raw = raw_text if raw_text is not None else self.read_small_text(path)
        combined = f"{path_text}\n{raw}".lower().replace("_", "-")

        blocked_contexts = self.BLOCKED_CONTEXTS_BY_ENTITY.get(entity_id_l, [])
        product_aliases = self.PRODUCT_ALIASES_BY_ENTITY.get(entity_id_l, [])
        related_product_aliases = self.RELATED_PRODUCT_ALIASES_BY_ENTITY.get(entity_id_l, [])
        insurer_aliases = self.INSURER_ALIASES_BY_ENTITY.get(entity_id_l, [])

        blocked_hits = [alias for alias in blocked_contexts if self.normalize(alias) in combined]
        if blocked_hits:
            return {"matched": False, "reason": "blocked_context", "matched_aliases": blocked_hits}

        related_hits = [alias for alias in related_product_aliases if self.normalize(alias) in combined]
        if related_hits:
            return {"matched": False, "reason": "not_entity_match", "matched_aliases": related_hits}

        product_hits = [alias for alias in product_aliases if self.normalize(alias) in combined]
        if product_aliases and product_hits:
            return {"matched": True, "reason": "strong_product_match", "matched_aliases": product_hits}

        insurer_hits = [alias for alias in insurer_aliases if self.normalize(alias) in combined]
        if product_aliases and insurer_hits and not product_hits:
            return {"matched": False, "reason": "not_entity_match", "matched_aliases": insurer_hits}

        if not product_aliases and insurer_hits:
            return {"matched": True, "reason": "insurer_match", "matched_aliases": insurer_hits}

        return {"matched": False, "reason": "not_entity_match", "matched_aliases": []}

    def find_field_hits(self, field: str, text: str) -> list[str]:
        normalized = self.normalize(text)
        hits = []
        for keyword in self.FIELD_KEYWORDS.get(field, []):
            keyword_l = self.normalize(keyword)
            if keyword_l and keyword_l in normalized:
                hits.append(keyword)
        return sorted(set(hits))

    def read_small_text(self, path: Path, limit: int | None = None) -> str:
        limit = limit or self.READ_LIMIT
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")[:limit]
        except Exception:
            return ""

        if path.suffix.lower() == ".json":
            try:
                data = json.loads(raw)
                return self.flatten_json_to_text(data)[:limit].lower().replace("_", "-")
            except Exception:
                pass

        return raw.lower().replace("_", "-")

    def flatten_json_to_text(self, data: Any) -> str:
        parts: list[str] = []

        def walk(obj: Any):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    parts.append(str(key))
                    walk(value)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
            elif isinstance(obj, (str, int, float, bool)):
                parts.append(str(obj))

        walk(data)
        return "\n".join(parts)

    def file_hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
        except Exception:
            digest.update(str(path).encode("utf-8"))
        return digest.hexdigest()

    def stable_id(self, prefix: str, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:20]
        return f"{prefix}_{digest}"

    def logical_document_key(self, path: Path, source_type: str) -> str:
        relative = str(path.relative_to(BASE_DIR)).lower().replace("\\", "/")
        stem = path.stem.lower()

        # Remove common parser/metadata suffixes so related representations group together.
        stem = re.sub(r"(_|-)?(metadata|parsed|sections|html-sections|html_sections|text|ocr)$", "", stem)
        stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")

        parent = str(path.parent.relative_to(BASE_DIR)).lower().replace("\\", "/")
        parent = re.sub(r"/(metadata|parsed|sections|html-sections|html_sections)$", "", parent)

        return f"{source_type}|{parent}|{stem or relative}"

    def safe_file_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def safe_modified_at(self, path: Path) -> str | None:
        try:
            return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        except OSError:
            return None

    def looks_like_metadata(self, raw_text: str) -> bool:
        metadata_terms = ["metadata", "content-type", "downloaded-at", "source-url", "file-path"]
        normalized = self.normalize(raw_text)
        return any(term in normalized for term in metadata_terms)

    def normalize(self, value: str) -> str:
        return value.lower().replace("_", "-")


def main():
    router = EvidenceRouter()
    plan = router.resolve_search_plan(
        entity_id="aditya_birla_health:activ_one",
        field="copay",
    )

    print("=" * 70)
    print("EVIDENCE ROUTER SANITY CHECK")
    print("=" * 70)
    print(f"Entity     : {plan['entity_id']}")
    print(f"Field      : {plan['field']}")
    print(f"Version    : {plan['router_version']}")
    print(f"Candidates : {plan['candidate_count']}")
    print(f"Bundles    : {plan['bundle_count']}")
    print(f"Rejected   : {plan['rejected_counts']}")
    print("Priority   : " + " > ".join(plan["priority_sources"]))

    for item in plan["candidates"][:20]:
        print(
            f"[{item['source_type']}] "
            f"[score={item['routing_score']}] "
            f"[{item['match_reason']}] "
            f"{item['relative_path']}"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
