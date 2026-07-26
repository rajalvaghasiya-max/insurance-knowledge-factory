from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.validators.health_domain_validator import HealthDomainValidator


class RoomRentExtractor:
    """
    Room Rent Extractor v0.2

    Fixes over v0.1:
        - Entity/path guard to reduce cross-product contamination
        - Stronger source filtering
        - Prefer "No Limit" and room category over accidental INR matches
        - Better handling of "without a limit" evidence
    """

    VERSION = "0.2"

    ROOM_RENT_KEYWORDS = [
        "room rent",
        "room category",
        "room eligibility",
        "eligible room",
        "hospital room",
        "single private",
        "private room",
        "shared room",
        "icu",
        "proportionate deduction",
        "without a limit",
        "no limit",
        "no capping",
    ]

    # Order matters. Strong semantic statements first.
    ROOM_PATTERNS = [
        # No room rent limit / without room rent capping
        re.compile(
            r"((?:room\s+rent[^.:\n]{0,80})?(?:no|without)\s+(?:a\s+)?(?:room\s+rent\s+)?(?:capping|cap|limit|restriction)[^.:\n]{0,80})",
            re.IGNORECASE,
        ),
        # Single Private Room / Any Room / Shared Room
        re.compile(
            r"((?P<category>single\s+private(?:\s+ac)?\s+room|any\s+room|private\s+room|shared\s+room|twin\s+sharing\s+room|single\s+standard\s+room))",
            re.IGNORECASE,
        ),
        # Room rent: 1% of Sum Insured
        re.compile(
            r"(room\s+rent[^.:\n]{0,80}[:\-]?\s*(?P<num>\d+(?:\.\d+)?)\s*%[^.:\n]{0,80}(?:sum\s+insured|si))",
            re.IGNORECASE,
        ),
        # Room rent up to Rs 5000 / day
        re.compile(
            r"(room\s+rent[^.:\n]{0,100}(?:rs\.?|₹|inr)\s*(?P<amount>\d[\d,]*)[^.:\n]{0,50}(?:per\s+day|/day|daily|day)?)",
            re.IGNORECASE,
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
        enforce_entity_guard: bool = True,
    ) -> dict[str, Any]:
        candidates = []
        skipped_by_entity_guard = 0
        files_scanned = 0

        entity_tokens = self.entity_tokens(entity_id)

        for path in self.iter_supported_files(search_root):
            if enforce_entity_guard and not self.path_matches_entity(path, entity_tokens):
                skipped_by_entity_guard += 1
                continue

            files_scanned += 1
            text = self.read_text_from_file(path)

            if not text:
                continue

            matches = self.find_room_rent_matches(text)

            for match_info in matches:
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
                "field": "room_rent_limit",
                "status": "not_found",
                "message": "No room rent limit evidence found within entity scope.",
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
            "field": "room_rent_limit",
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
        tokens = {t for t in tokens if t and t not in {"health", "insurance", "product"}}

        # Known aliases for current product.
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

    def path_matches_entity(self, path: Path, entity_tokens: set[str]) -> bool:
        path_text = str(path).lower().replace("\\", "/")
        name_text = path.name.lower()

        # Strong match: insurer/product folder names in path.
        if "aditya_birla_health" in entity_tokens and "aditya_birla_health" in path_text:
            return True

        if "activ_one" in entity_tokens and ("activ_one" in path_text or "active-one" in path_text or "activ-one" in path_text):
            return True

        # If scanning a product-specific folder, allow all files in it.
        if any(token in path_text for token in entity_tokens if len(token) >= 5):
            return True

        # For hashed parsed files, filename may not contain entity. Parent folder may contain insurer.
        parent_text = str(path.parent).lower().replace("\\", "/")
        if "aditya_birla_health" in parent_text and {"activ", "one"} & entity_tokens:
            return True

        return False

    def iter_supported_files(self, root: Path):
        if not root.exists():
            return

        supported = {".json", ".txt", ".md"}

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue

            if path.suffix.lower() not in supported:
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

    def find_room_rent_matches(self, text: str) -> list[dict[str, Any]]:
        normalized = re.sub(r"\s+", " ", text)
        
        matches = []
        seen_match_keys: set[tuple[int, int, str]] = set()

        lower = normalized.lower()

        keyword_positions = []

        for keyword in self.ROOM_RENT_KEYWORDS:
            start = 0
            while True:
                idx = lower.find(keyword, start)
                if idx == -1:
                    break
                keyword_positions.append(idx)
                start = idx + len(keyword)

        windows = []

        for pos in keyword_positions:
            window_start = max(0, pos - 300)
            window_end = min(len(normalized), pos + 500)
            windows.append((window_start, normalized[window_start:window_end]))

        for window_start, window in windows:
            for pattern in self.ROOM_PATTERNS:
                for match in pattern.finditer(window):
                    absolute_start = window_start + match.start()
                    absolute_end = window_start + match.end()
                    match_key = (
                        absolute_start,
                        absolute_end,
                        pattern.pattern,
                    )

                    if match_key in seen_match_keys:
                        continue

                    seen_match_keys.add(match_key)
                    matches.append(
                        {
                            "match": match,
                            "absolute_start": absolute_start,
                            "window": window,
                            "pattern": pattern.pattern,
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
        evidence_text = self.clean_evidence(match.group(1))

        value, unit, raw_value, value_type = self.normalize_room_value(match, evidence_text)

        try:
            relative_path = path.relative_to(BASE_DIR)
        except ValueError:
            relative_path = path

        return {
            "fact_id": f"fact:{entity_id}:room_rent_limit",
            "entity_id": entity_id,
            "entity_type": "product",
            "insurance_line": insurance_line,
            "field": "room_rent_limit",
            "value": value,
            "raw_value": raw_value,
            "unit": unit,
            "metadata": {
                "value_type": value_type,
                "proportionate_deduction_detected_nearby": self.detect_proportionate_deduction(match_info["window"]),
            },
            "evidence": {
                "text": evidence_text,
                "evidence_type": "clause",
                "page": None,
                "section": self.infer_section(full_text, match_info["absolute_start"]),
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
                "score": self.estimate_confidence(value_type, match_info["window"]),
                "method": "regex",
                "reason": "Matched room rent phrase using rule-based pattern.",
                "requires_review": False,
            },
            "extraction": {
                "agent_name": "room_rent_extractor",
                "agent_version": self.VERSION,
                "extracted_at": self.utc_now(),
                "parser_version": None,
                "model_name": None,
            },
        }

    def normalize_room_value(self, match: re.Match, evidence_text: str) -> tuple[Any, str | None, str, str]:
        groupdict = match.groupdict()
        evidence_l = evidence_text.lower()

        if re.search(
            r"(?:no|without)\s+(?:a\s+)?(?:room\s+rent\s+)?"
            r"(?:capping|cap|limit|restriction)",
            evidence_l,
        ):
            return "No Limit", "text", "No room rent limit", "no_limit"

        if groupdict.get("category"):
            category = self.title_case_room_category(groupdict["category"])
            return category, "room_category", category, "room_category"

        if groupdict.get("num"):
            number = float(groupdict["num"])
            if number.is_integer():
                number = int(number)
            return number, "percent", f"{number}% of Sum Insured", "percentage_of_sum_insured"

        if groupdict.get("amount"):
            amount = int(groupdict["amount"].replace(",", ""))
            return amount, "INR", f"INR {amount} per day", "fixed_amount"

        return evidence_text, "text", evidence_text, "text"

    def title_case_room_category(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        return text.title().replace("Ac", "AC")

    def detect_proportionate_deduction(self, text: str) -> bool:
        return bool(
            re.search(
                r"proportionate|proportionately|proportionate\s+deduction|associated\s+medical\s+expenses",
                text,
                re.IGNORECASE,
            )
        )

    def estimate_confidence(self, value_type: str, window: str) -> float:
        score = 0.78

        if value_type == "no_limit":
            score += 0.12
        elif value_type in {"percentage_of_sum_insured", "fixed_amount", "room_category"}:
            score += 0.08

        if "room rent" in window.lower():
            score += 0.06

        return min(score, 0.94)

    def clean_evidence(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > 500:
            return text[:500].strip() + "..."

        return text

    def infer_section(self, full_text: str, match_start: int) -> str | None:
        before = full_text[:match_start]
        lines = [line.strip() for line in before.splitlines() if line.strip()]

        for line in reversed(lines[-25:]):
            if len(line) <= 100 and any(
                token in line.lower()
                for token in ["room", "rent", "hospitalisation", "hospitalization", "benefit", "sub-limit"]
            ):
                return line

        return "Room Rent"

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
            value_type = candidate.get("metadata", {}).get("value_type")

            value = 0

            if source_type == "policy_wording":
                value += 60
            elif source_type == "customer_information_sheet":
                value += 50
            elif source_type == "brochure":
                value += 40
            elif source_type == "webpage":
                value += 20

            if value_type == "no_limit":
                value += 45
            elif value_type == "room_category":
                value += 35
            elif value_type == "percentage_of_sum_insured":
                value += 30
            elif value_type == "fixed_amount":
                value += 20

            if "room rent" in evidence:
                value += 25

            if "without a limit" in evidence or "no limit" in evidence:
                value += 40

            if candidate.get("metadata", {}).get("proportionate_deduction_detected_nearby"):
                value += 5

            return value

        return sorted(candidates, key=score, reverse=True)[0]
