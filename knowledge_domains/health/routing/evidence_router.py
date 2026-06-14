from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


class EvidenceRouter:
    """
    Evidence Router v0.3

    Fixes over v0.1:
        - Product-level guard: insurer match alone is not enough.
        - Reject unrelated Aditya Birla life/motor/pension/travel pages for Activ One.
        - Require product token match for product-specific routing.
        - Archive metadata is kept only when URL/path/title/content contains product token.
    """

    VERSION = "0.3"

    FIELD_SOURCE_PRIORITY = {
        "ped_waiting_period": [
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
        "prospectus": [
            "prospectus",
        ],
        "brochure": [
            "brochure",
        ],
        "webpage": [
            "html_sections",
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

    def get_priority_sources(self, field: str) -> list[str]:
        return self.FIELD_SOURCE_PRIORITY.get(
            field,
            ["policy_wording", "customer_information_sheet", "brochure", "webpage"],
        )

    def resolve_search_plan(
        self,
        *,
        entity_id: str,
        field: str,
        base_roots: list[str] | None = None,
    ) -> dict[str, Any]:
        if base_roots is None:
            base_roots = [
                "knowledge",
                "parsed",
                "archive",
            ]

        priority_sources = self.get_priority_sources(field)

        candidates = []
        rejected_counts = {
            "not_entity_match": 0,
            "blocked_context": 0,
            "unsupported_source_type": 0,
        }

        for root_str in base_roots:
            root = BASE_DIR / root_str

            if not root.exists():
                continue

            for path in self.iter_supported_files(root):
                match_result = self.path_matches_entity(path, entity_id)

                if not match_result["matched"]:
                    rejected_counts[match_result["reason"]] = rejected_counts.get(match_result["reason"], 0) + 1
                    continue

                source_type = self.classify_source_type(path)

                if source_type == "extracted_fact":
                    rejected_counts["unsupported_source_type"] += 1
                    continue

                if source_type not in priority_sources:
                    rejected_counts["unsupported_source_type"] += 1
                    continue

                candidates.append(
                    {
                        "path": str(path),
                        "relative_path": str(path.relative_to(BASE_DIR)).replace("\\", "/"),
                        "source_type": source_type,
                        "priority": priority_sources.index(source_type),
                        "match_reason": match_result["reason"],
                    }
                )

        candidates = sorted(
            candidates,
            key=lambda x: (
                x["priority"],
                0 if x["match_reason"] == "strong_product_match" else 1,
                x["relative_path"],
            ),
        )

        return {
            "entity_id": entity_id,
            "field": field,
            "router_version": self.VERSION,
            "priority_sources": priority_sources,
            "candidate_count": len(candidates),
            "rejected_counts": rejected_counts,
            "candidates": candidates,
        }

    def iter_supported_files(self, root: Path):
        supported = {".json", ".txt", ".md"}

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue

            if path.suffix.lower() not in supported:
                continue

            lower = str(path).lower()

            if "routing_plans" in lower or "routing-plans" in lower:
                continue

            if "extracted_facts" in lower or "extracted-facts" in lower:
                continue

            if "\\.venv\\" in lower or "/.venv/" in lower:
                continue

            if path.stat().st_size > 5_000_000:
                continue

            yield path

    def classify_source_type(self, path: Path) -> str:
        text = str(path).lower().replace("\\", "/").replace("_", "-")

        if "html-sections" in text or "html_sections" in text:
            return "webpage"

        for source_type, hints in self.SOURCE_TYPE_HINTS.items():
            for hint in hints:
                hint_l = hint.lower().replace("_", "-")
                if hint_l in text:
                    return source_type

        if path.suffix.lower() == ".json":
            raw = self.read_small_text(path)

            if "policy wording" in raw or "policy_wording" in raw or "policy document" in raw:
                return "policy_wording"

            if "customer information sheet" in raw or "customer_information_sheet" in raw or " cis " in f" {raw} ":
                return "customer_information_sheet"

            if "brochure" in raw:
                return "brochure"

            if "prospectus" in raw:
                return "prospectus"

        return "webpage"

    def path_matches_entity(self, path: Path, entity_id: str) -> dict[str, Any]:
        entity_id_l = entity_id.lower()
        path_text = str(path).lower().replace("\\", "/").replace("_", "-")
        raw_text = self.read_small_text(path)

        combined = f"{path_text}\n{raw_text}"

        blocked_contexts = self.BLOCKED_CONTEXTS_BY_ENTITY.get(entity_id_l, [])
        product_aliases = self.PRODUCT_ALIASES_BY_ENTITY.get(entity_id_l, [])
        insurer_aliases = self.INSURER_ALIASES_BY_ENTITY.get(entity_id_l, [])

        for blocked in blocked_contexts:
            if blocked in combined:
                return {"matched": False, "reason": "blocked_context"}

        insurer_match = any(alias.lower().replace("_", "-") in combined for alias in insurer_aliases)
        product_match = any(alias.lower().replace("_", "-") in combined for alias in product_aliases)

        related_product_aliases = self.RELATED_PRODUCT_ALIASES_BY_ENTITY.get(entity_id_l, [])
        related_product_match = any(
            alias.lower().replace("_", "-") in combined
            for alias in related_product_aliases
        )

        # Reject sibling variants for product-level critical fields.
        # Example: Activ One Max should not be evidence for Activ One.
        if related_product_match:
            return {"matched": False, "reason": "not_entity_match"}

        # Product-specific entity must have product match.
        if product_aliases and product_match:
            return {"matched": True, "reason": "strong_product_match"}
            

        # For product-level extraction, insurer-only match is too broad.
        if product_aliases and insurer_match and not product_match:
            return {"matched": False, "reason": "not_entity_match"}

        if not product_aliases and insurer_match:
            return {"matched": True, "reason": "insurer_match"}

        return {"matched": False, "reason": "not_entity_match"}

    def read_small_text(self, path: Path, limit: int = 12000) -> str:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")[:limit]
        except Exception:
            return ""

        # For metadata JSON, include useful fields as searchable text.
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(raw)
                return self.flatten_json_to_text(data)[:limit].lower().replace("_", "-")
            except Exception:
                pass

        return raw.lower().replace("_", "-")

    def flatten_json_to_text(self, data: Any) -> str:
        parts = []

        def walk(obj: Any):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    parts.append(str(key))
                    walk(value)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
            elif isinstance(obj, (str, int, float)):
                parts.append(str(obj))

        walk(data)
        return "\n".join(parts)


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
    print(f"Rejected   : {plan['rejected_counts']}")
    print("Priority   : " + " > ".join(plan["priority_sources"]))

    for item in plan["candidates"][:20]:
        print(f"[{item['source_type']}] [{item['match_reason']}] {item['relative_path']}")

    print("=" * 70)


if __name__ == "__main__":
    main()
