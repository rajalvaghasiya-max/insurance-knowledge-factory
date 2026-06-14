from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.validators.health_domain_validator import HealthDomainValidator


class PedWaitingPeriodExtractor:
    """
    PED Waiting Period Extractor v0.1

    Purpose:
        Create the first evidence-backed health insurance fact:
        ped_waiting_period

    Design:
        - Lightweight rule/regex based
        - No LLM dependency
        - Produces evidence_schema-compatible fact object
        - Validates using HealthDomainValidator
    """

    VERSION = "0.1"

    PED_PATTERNS = [
        re.compile(
            r"(pre[- ]?existing\s+(?:disease|diseases|illness|condition|conditions).*?"
            r"(?:covered|coverage|waiting).*?"
            r"(?P<num>\d{1,2})\s*(?P<unit>months?|years?|days?))",
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r"(waiting\s+period\s+(?:for|of).*?pre[- ]?existing.*?"
            r"(?P<num>\d{1,2})\s*(?P<unit>months?|years?|days?))",
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r"(pre[- ]?existing.*?"
            r"(?P<num>\d{1,2})\s*(?P<unit>months?|years?|days?).*?"
            r"(?:waiting|covered|coverage))",
            re.IGNORECASE | re.DOTALL,
        ),
    ]

    def utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def extract_from_search_root(
        self,
        *,
        entity_id: str,
        search_root: Path,
        insurance_line: str = "health",
    ) -> dict[str, Any]:
        candidates = []

        for path in self.iter_supported_files(search_root):
            text = self.read_text_from_file(path)

            if not text:
                continue

            match = self.find_ped_match(text)

            if match:
                candidates.append(
                    self.build_candidate(
                        entity_id=entity_id,
                        insurance_line=insurance_line,
                        path=path,
                        match=match,
                        full_text=text,
                    )
                )

        best_fact = self.select_best_candidate(candidates)

        if best_fact is None:
            return {
                "entity_id": entity_id,
                "field": "ped_waiting_period",
                "status": "not_found",
                "message": "No PED waiting period evidence found.",
                "searched_root": str(search_root),
                "extracted_at": self.utc_now(),
            }

        validator = HealthDomainValidator()
        validation_report = validator.validate_facts(
            entity_id=entity_id,
            facts=[best_fact],
            validation_mode="fact",

        )

        best_fact["validation"] = {
            "status": validation_report["results"][0]["status"],
            "messages": validation_report["results"][0]["messages"],
            "review_recommendation": validation_report["review_recommendation"],
            "validated_at": validation_report["validated_at"],
            "validator_name": validation_report["validator_name"],
            "validator_version": validation_report["validator_version"],
        }

        return {
            "entity_id": entity_id,
            "field": "ped_waiting_period",
            "status": "extracted",
            "fact": best_fact,
            "validation_report": validation_report,
            "extracted_at": self.utc_now(),
        }

    def iter_supported_files(self, root: Path):
        if not root.exists():
            return

        supported = {".json", ".txt", ".md"}

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue

            if path.suffix.lower() not in supported:
                continue

            # Skip registry/config files and very large files for this first proof.
            lower = str(path).lower()

            if "\\.venv\\" in lower or "/.venv/" in lower:
                continue

            if path.stat().st_size > 5_000_000:
                continue

            yield path

    def read_text_from_file(self, path: Path) -> str:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

        if path.suffix.lower() == ".json":
            try:
                data = json.loads(raw)
                return self.flatten_json_to_text(data)
            except Exception:
                return raw

        return raw

    def flatten_json_to_text(self, data: Any) -> str:
        parts = []

        def walk(obj: Any):
            if isinstance(obj, dict):
                for value in obj.values():
                    walk(value)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
            elif isinstance(obj, (str, int, float)):
                parts.append(str(obj))

        walk(data)
        return "\n".join(parts)

    def find_ped_match(self, text: str) -> re.Match | None:
        normalized = re.sub(r"\s+", " ", text)

        for pattern in self.PED_PATTERNS:
            match = pattern.search(normalized)

            if match:
                return match

        return None

    def build_candidate(
        self,
        *,
        entity_id: str,
        insurance_line: str,
        path: Path,
        match: re.Match,
        full_text: str,
    ) -> dict[str, Any]:
        number = int(match.group("num"))
        raw_unit = match.group("unit").lower()

        if raw_unit.startswith("year"):
            value = number * 12
            unit = "months"
            raw_value = f"{number} years"
        elif raw_unit.startswith("day"):
            value = round(number / 30, 2)
            unit = "months"
            raw_value = f"{number} days"
        else:
            value = number
            unit = "months"
            raw_value = f"{number} months"

        evidence_text = self.clean_evidence(match.group(1))

        relative_path = path.relative_to(BASE_DIR) if path.is_relative_to(BASE_DIR) else path

        return {
            "fact_id": f"fact:{entity_id}:ped_waiting_period",
            "entity_id": entity_id,
            "entity_type": "product",
            "insurance_line": insurance_line,
            "field": "ped_waiting_period",
            "value": value,
            "raw_value": raw_value,
            "unit": unit,
            "evidence": {
                "text": evidence_text,
                "evidence_type": "clause",
                "page": None,
                "section": self.infer_section(full_text, match.start()),
                "table_id": None,
                "row_id": None,
                "chunk_id": None,
            },
            "source": {
                "source_document": path.name,
                "source_type": self.infer_source_type(path),
                "source_url": None,
                "source_file_path": str(relative_path).replace("\\", "/"),
                "source_hash": None,
                "document_version": None,
                "effective_date": None,
            },
            "confidence": {
                "score": 0.82,
                "method": "regex",
                "reason": "Matched PED waiting period phrase using rule-based pattern.",
                "requires_review": False,
            },
            "extraction": {
                "agent_name": "ped_waiting_period_extractor",
                "agent_version": self.VERSION,
                "extracted_at": self.utc_now(),
                "parser_version": None,
                "model_name": None,
            },
        }

    def clean_evidence(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > 500:
            return text[:500].strip() + "..."

        return text

    def infer_section(self, full_text: str, match_start: int) -> str | None:
        before = full_text[:match_start]
        lines = [line.strip() for line in before.splitlines() if line.strip()]

        for line in reversed(lines[-20:]):
            if len(line) <= 80 and any(
                token in line.lower()
                for token in ["waiting", "exclusion", "pre-existing", "disease"]
            ):
                return line

        return "Waiting Periods"

    def infer_source_type(self, path: Path) -> str:
        lower = path.name.lower()

        if "policy" in lower or "wording" in lower:
            return "policy_wording"

        if "brochure" in lower:
            return "brochure"

        if "cis" in lower or "customer_information" in lower:
            return "customer_information_sheet"

        if "prospectus" in lower:
            return "prospectus"

        if path.suffix.lower() == ".json":
            return "webpage"

        return "unknown"

    def select_best_candidate(self, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates:
            return None

        def score(candidate: dict[str, Any]) -> int:
            source_type = candidate.get("source", {}).get("source_type")
            evidence = candidate.get("evidence", {}).get("text", "").lower()

            value = 0

            if source_type == "policy_wording":
                value += 50
            elif source_type == "customer_information_sheet":
                value += 40
            elif source_type == "brochure":
                value += 30

            if "pre-existing" in evidence or "pre existing" in evidence:
                value += 20

            if "waiting" in evidence:
                value += 10

            return value

        return sorted(candidates, key=score, reverse=True)[0]
