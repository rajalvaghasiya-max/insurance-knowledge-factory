from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.validators.health_domain_validator import (
    HealthDomainValidator,
)


class InitialWaitingPeriodExtractor:
    """
    Initial Waiting Period Extractor v0.1.

    Extracts the initial policy waiting period and whether an accident
    exception is explicitly stated in the supporting evidence.
    """

    VERSION = "0.1"

    INITIAL_WAITING_PERIOD_PATTERNS = [
        re.compile(
            r"("
            r"initial\s+waiting\s+period"
            r".{0,260}?"
            r"(?:first\s+)?"
            r"(?P<num>\d{1,3})\s*[- ]?(?P<unit>days?|months?|years?)"
            r")",
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r"("
            r"(?P<num>\d{1,3})\s*[- ]?(?P<unit>days?|months?|years?)"
            r"\s+initial\s+waiting\s+period"
            r")",
            re.IGNORECASE,
        ),
    ]

    INITIAL_WAITING_PERIOD_KEYWORDS = [
        "initial waiting period",
        "first 30 days",
        "first 60 days",
        "first 90 days",
    ]

    def utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def extract_from_search_root(
        self,
        *,
        entity_id: str,
        search_root: Path,
        insurance_line: str = "health",
        enforce_entity_guard: bool = True,
    ) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        skipped_by_entity_guard = 0
        files_scanned = 0
        entity_tokens = self.entity_tokens(entity_id)

        for path in self.iter_supported_files(search_root):
            if enforce_entity_guard and not self.path_matches_entity(
                path,
                entity_tokens,
            ):
                skipped_by_entity_guard += 1
                continue

            files_scanned += 1
            text = self.read_text_from_file(path)

            if not text:
                continue

            for match_info in self.find_initial_waiting_period_matches(text):
                candidates.append(
                    self.build_candidate(
                        entity_id=entity_id,
                        insurance_line=insurance_line,
                        path=path,
                        match_info=match_info,
                        full_text=text,
                    )
                )

        best_fact = self.select_best_candidate(candidates)

        if best_fact is None:
            return {
                "entity_id": entity_id,
                "field": "initial_waiting_period",
                "status": "not_found",
                "message": (
                    "No initial waiting period evidence found within "
                    "entity scope."
                ),
                "searched_root": str(search_root),
                "files_scanned": files_scanned,
                "skipped_by_entity_guard": skipped_by_entity_guard,
                "candidate_count": len(candidates),
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
            "field": "initial_waiting_period",
            "status": "extracted",
            "fact": best_fact,
            "validation_report": validation_report,
            "candidate_count": len(candidates),
            "files_scanned": files_scanned,
            "skipped_by_entity_guard": skipped_by_entity_guard,
            "extracted_at": self.utc_now(),
        }

    def entity_tokens(self, entity_id: str) -> set[str]:
        raw = entity_id.lower()

        tokens = set(re.split(r"[:_\-/\s]+", raw))
        tokens = {
            token
            for token in tokens
            if token and token not in {"health", "insurance", "product"}
        }

        alias_map = {
            "aditya_birla_health:activ_one": {
                "aditya",
                "birla",
                "aditya_birla_health",
                "activ",
                "active",
                "one",
                "activ_one",
                "active_one",
            }
        }

        tokens.update(alias_map.get(raw, set()))
        return tokens

    def path_matches_entity(
        self,
        path: Path,
        entity_tokens: set[str],
    ) -> bool:
        path_text = str(path).lower().replace("\\", "/")

        if (
            "aditya_birla_health" in entity_tokens
            and "aditya_birla_health" in path_text
        ):
            return True

        if (
            "activ_one" in entity_tokens
            and (
                "activ_one" in path_text
                or "active-one" in path_text
                or "activ-one" in path_text
            )
        ):
            return True

        if any(
            token in path_text
            for token in entity_tokens
            if len(token) >= 5
        ):
            return True

        parent_text = str(path.parent).lower().replace("\\", "/")

        if (
            "aditya_birla_health" in parent_text
            and {"activ", "one"} & entity_tokens
        ):
            return True

        return False

    def iter_supported_files(self, root: Path):
        if not root.exists():
            return

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue

            if path.suffix.lower() not in {".json", ".txt", ".md"}:
                continue

            lower = str(path).lower()

            if "\\.venv\\" in lower or "/.venv/" in lower:
                continue

            if path.stat().st_size > 5_000_000:
                continue

            yield path

    def read_text_from_file(self, path: Path) -> str:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

        if path.suffix.lower() != ".json":
            return raw

        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return raw

        return self.flatten_json_to_text(loaded)

    def flatten_json_to_text(self, data: Any) -> str:
        parts: list[str] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
            elif isinstance(value, (str, int, float)):
                parts.append(str(value))

        walk(data)
        return "\n".join(parts)

    def find_initial_waiting_period_matches(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        normalized = re.sub(r"\s+", " ", text)
        matches: list[dict[str, Any]] = []
        seen_match_keys: set[tuple[int, int]] = set()

        for pattern in self.INITIAL_WAITING_PERIOD_PATTERNS:
            for match in pattern.finditer(normalized):
                match_key = (match.start(), match.end())

                if match_key in seen_match_keys:
                    continue

                seen_match_keys.add(match_key)

                matches.append(
                    {
                        "match": match,
                        "absolute_start": match.start(),
                        "window": normalized[
                            max(0, match.start() - 250):
                            min(len(normalized), match.end() + 250)
                        ],
                    }
                )

        return matches

    def build_candidate(
        self,
        *,
        entity_id: str,
        insurance_line: str,
        path: Path,
        match_info: dict[str, Any],
        full_text: str,
    ) -> dict[str, Any]:
        match = match_info["match"]
        number = int(match.group("num"))
        raw_unit = match.group("unit").lower()
        unit = {
            "day": "days",
            "days": "days",
            "month": "months",
            "months": "months",
            "year": "years",
            "years": "years",
        }[raw_unit]
        evidence_text = self.clean_evidence(match.group(1))
        accident_exception = self.detect_accident_exception(
            match_info["window"]
        )

        try:
            relative_path = path.relative_to(BASE_DIR)
        except ValueError:
            relative_path = path

        return {
            "fact_id": f"fact:{entity_id}:initial_waiting_period",
            "entity_id": entity_id,
            "entity_type": "product",
            "insurance_line": insurance_line,
            "field": "initial_waiting_period",
            "value": number,
            "raw_value": f"{number} {unit}",
            "unit": unit,
            "metadata": {
                "value_type": "duration",
                "accident_exception": accident_exception,
            },
            "evidence": {
                "text": evidence_text,
                "evidence_type": "clause",
                "page": None,
                "section": self.infer_section(
                    full_text,
                    match_info["absolute_start"],
                ),
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
                "score": self.estimate_confidence(
                    evidence_text,
                    accident_exception,
                ),
                "method": "regex",
                "reason": (
                    "Matched initial waiting period phrase using "
                    "rule-based pattern."
                ),
                "requires_review": False,
            },
            "extraction": {
                "agent_name": "initial_waiting_period_extractor",
                "agent_version": self.VERSION,
                "extracted_at": self.utc_now(),
                "parser_version": None,
                "model_name": None,
            },
        }

    def detect_accident_exception(self, text: str) -> bool | str:
        normalized = re.sub(r"\s+", " ", text).lower()

        if re.search(
            r"(?:except|excluding|other\s+than)"
            r".{0,80}"
            r"(?:accident|accidental)",
            normalized,
        ):
            return True

        return "unknown"

    def estimate_confidence(
        self,
        evidence_text: str,
        accident_exception: bool | str,
    ) -> float:
        score = 0.82
        normalized = evidence_text.lower()

        if "initial waiting period" in normalized:
            score += 0.08

        if accident_exception is True:
            score += 0.03

        return min(score, 0.93)

    def clean_evidence(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()

        if len(cleaned) > 500:
            return cleaned[:500].strip() + "..."

        return cleaned

    def infer_section(
        self,
        full_text: str,
        match_start: int,
    ) -> str:
        before = full_text[:match_start]
        lines = [
            line.strip()
            for line in before.splitlines()
            if line.strip()
        ]

        for line in reversed(lines[-20:]):
            if len(line) <= 100 and any(
                token in line.lower()
                for token in ["waiting", "initial", "exclusion", "claim"]
            ):
                return line

        return "Initial Waiting Period"

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

    def select_best_candidate(
        self,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not candidates:
            return None

        def score(candidate: dict[str, Any]) -> int:
            source_type = candidate.get("source", {}).get("source_type")
            evidence = candidate.get("evidence", {}).get("text", "").lower()
            score_value = 0

            if source_type == "policy_wording":
                score_value += 60
            elif source_type == "customer_information_sheet":
                score_value += 50
            elif source_type == "brochure":
                score_value += 40
            elif source_type == "webpage":
                score_value += 20

            if "initial waiting period" in evidence:
                score_value += 30

            if "accident" in evidence:
                score_value += 5

            return score_value

        return sorted(candidates, key=score, reverse=True)[0]