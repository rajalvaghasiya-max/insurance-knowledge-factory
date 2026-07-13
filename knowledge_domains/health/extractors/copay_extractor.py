from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.validators.health_domain_validator import HealthDomainValidator


class CopayExtractor:
    """Co-pay Extractor v0.1"""

    VERSION = "0.1"

    COPAY_KEYWORDS = [
        "co-pay", "copay", "co payment", "co-payment", "co pay",
        "co-insurance", "coinsurance", "no co-pay", "no copay", "zero co-pay",
    ]

    COPAY_PATTERNS = [
        re.compile(r"((?:no|zero|nil|without)\s+(?:co[- ]?pay|copay|co[- ]?payment|co[- ]?insurance))", re.I),
        re.compile(r"((?P<pct>\d{1,3})\s*%\s*(?:co[- ]?pay|copay|co[- ]?payment|co[- ]?insurance)[^.:\n]{0,160})", re.I),
        re.compile(
            r"((?:co[- ]?pay|copay|co[- ]?payment|co[- ]?insurance)"
            r"[^.:\n]{0,120}?(?P<pct>\d{1,3})\s*%)",
            re.I,
        ),
    ]

    def utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def extract_from_search_root(self, *, entity_id: str, search_root: Path, insurance_line: str = "health", enforce_entity_guard: bool = True) -> dict[str, Any]:
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

            for match_info in self.find_copay_matches(text):
                candidates.append(self.build_candidate(entity_id=entity_id, insurance_line=insurance_line, path=path, match_info=match_info, full_text=text))

        best_fact = self.select_best_candidate(candidates)

        if best_fact is None:
            return {
                "entity_id": entity_id,
                "field": "copay",
                "status": "not_found",
                "message": "No co-pay evidence found within entity scope.",
                "searched_root": str(search_root),
                "files_scanned": files_scanned,
                "skipped_by_entity_guard": skipped_by_entity_guard,
                "candidate_count": len(candidates),
                "extracted_at": self.utc_now(),
            }

        validator = HealthDomainValidator()
        validation_report = validator.validate_facts(entity_id=entity_id, facts=[best_fact], validation_mode="fact")
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
            "field": "copay",
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
        alias_map = {
            "aditya_birla_health:activ_one": {"aditya", "birla", "aditya_birla_health", "activ", "active", "one", "activ_one", "active_one"}
        }
        tokens.update(alias_map.get(raw, set()))
        return tokens

    def path_matches_entity(self, path: Path, entity_tokens: set[str]) -> bool:
        path_text = str(path).lower().replace("\\", "/")
        if "aditya_birla_health" in entity_tokens and "aditya_birla_health" in path_text:
            return True
        if "activ_one" in entity_tokens and ("activ_one" in path_text or "active-one" in path_text or "activ-one" in path_text):
            return True
        if any(token in path_text for token in entity_tokens if len(token) >= 5):
            return True
        parent_text = str(path.parent).lower().replace("\\", "/")
        if "aditya_birla_health" in parent_text and {"activ", "one"} & entity_tokens:
            return True
        return False

    def iter_supported_files(self, root: Path):
        if not root.exists():
            return
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".txt", ".md"}:
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
                return self.flatten_json_to_text(json.loads(raw))
            except Exception:
                return raw
        return raw

    def flatten_json_to_text(self, data: Any) -> str:
        parts = []
        def walk(obj: Any):
            if isinstance(obj, dict):
                for value in obj.values(): walk(value)
            elif isinstance(obj, list):
                for item in obj: walk(item)
            elif isinstance(obj, (str, int, float)):
                parts.append(str(obj))
        walk(data)
        return "\n".join(parts)

    def find_copay_matches(self, text: str) -> list[dict[str, Any]]:
        normalized = re.sub(r"\s+", " ", text)
        lower = normalized.lower()
        matches = []
        positions = []
        for keyword in self.COPAY_KEYWORDS:
            start = 0
            while True:
                idx = lower.find(keyword, start)
                if idx == -1: break
                positions.append(idx)
                start = idx + len(keyword)
        for pos in positions:
            window_start = max(0, pos - 300)
            window_end = min(len(normalized), pos + 500)
            window = normalized[window_start:window_end]
            for pattern in self.COPAY_PATTERNS:
                for match in pattern.finditer(window):
                    matches.append({"match": match, "absolute_start": window_start + match.start(), "window": window})
        return matches

    def build_candidate(self, *, entity_id: str, insurance_line: str, path: Path, match_info: dict[str, Any], full_text: str) -> dict[str, Any]:
        match = match_info["match"]
        evidence_text = self.clean_evidence(match.group(1))
        value, unit, raw_value, value_type, applicability = self.normalize_copay_value(match, evidence_text, match_info["window"])
        try:
            relative_path = path.relative_to(BASE_DIR)
        except ValueError:
            relative_path = path
        return {
            "fact_id": f"fact:{entity_id}:copay",
            "entity_id": entity_id,
            "entity_type": "product",
            "insurance_line": insurance_line,
            "field": "copay",
            "value": value,
            "raw_value": raw_value,
            "unit": unit,
            "metadata": {"value_type": value_type, "applicability": applicability, "conditional": applicability not in {"not_applicable", "all_claims", "unknown"}},
            "evidence": {"text": evidence_text, "evidence_type": "clause", "page": None, "section": self.infer_section(full_text, match_info["absolute_start"]), "table_id": None, "row_id": None, "chunk_id": None},
            "source": {"source_document": path.name, "source_type": self.infer_source_type(path), "source_url": None, "source_file_path": str(relative_path).replace("\\", "/"), "source_hash": None, "document_version": None, "effective_date": None},
            "confidence": {"score": self.estimate_confidence(value_type, match_info["window"]), "method": "regex", "reason": "Matched co-pay phrase using rule-based pattern.", "requires_review": False},
            "extraction": {"agent_name": "copay_extractor", "agent_version": self.VERSION, "extracted_at": self.utc_now(), "parser_version": None, "model_name": None},
        }

    def normalize_copay_value(self, match: re.Match, evidence_text: str, window: str) -> tuple[Any, str | None, str, str, str]:
        evidence_l = evidence_text.lower()
        if re.search(r"(?:no|zero|nil|without)\s+(?:co[- ]?pay|copay|co[- ]?payment|co[- ]?insurance)", evidence_l):
            return 0, "percent", "No co-pay", "no_copay", "not_applicable"
        pct = match.groupdict().get("pct")
        if pct is not None:
            percentage = int(pct)
            return percentage, "percent", f"{percentage}% co-pay", "percentage", self.infer_applicability(window.lower())
        return evidence_text, "text", evidence_text, "text", "unknown"

    def infer_applicability(self, text: str) -> str:
        if any(token in text for token in ["age", "senior citizen", "above", "60", "61", "65"]): return "age_based"
        if any(token in text for token in ["zone", "city", "metro", "non-metro"]): return "zone_based"
        if any(token in text for token in ["treatment", "disease", "procedure"]): return "treatment_based"
        if any(token in text for token in ["network", "non-network", "hospital"]): return "hospital_based"
        if "all claim" in text or "each claim" in text or "every claim" in text: return "all_claims"
        return "unknown"

    def estimate_confidence(self, value_type: str, window: str) -> float:
        score = 0.78
        if value_type == "no_copay": score += 0.12
        elif value_type == "percentage": score += 0.10
        if "co" in window.lower() and ("pay" in window.lower() or "payment" in window.lower()): score += 0.05
        return min(score, 0.94)

    def clean_evidence(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        return text[:500].strip() + "..." if len(text) > 500 else text

    def infer_section(self, full_text: str, match_start: int) -> str | None:
        before = full_text[:match_start]
        lines = [line.strip() for line in before.splitlines() if line.strip()]
        for line in reversed(lines[-25:]):
            if len(line) <= 100 and any(token in line.lower() for token in ["co-pay", "copay", "co payment", "claim", "deductible", "cost sharing"]):
                return line
        return "Co-pay"

    def infer_source_type(self, path: Path) -> str:
        lower = path.name.lower()
        if "policy" in lower or "wording" in lower: return "policy_wording"
        if "brochure" in lower: return "brochure"
        if "cis" in lower or "customer_information" in lower: return "customer_information_sheet"
        if "prospectus" in lower: return "prospectus"
        if path.suffix.lower() == ".json": return "webpage"
        return "unknown"

    def select_best_candidate(self, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates: return None
        def score(candidate: dict[str, Any]) -> int:
            source_type = candidate.get("source", {}).get("source_type")
            evidence = candidate.get("evidence", {}).get("text", "").lower()
            value_type = candidate.get("metadata", {}).get("value_type")
            value = 0
            if source_type == "policy_wording": value += 60
            elif source_type == "customer_information_sheet": value += 50
            elif source_type == "brochure": value += 40
            elif source_type == "webpage": value += 20
            if value_type == "no_copay": value += 40
            elif value_type == "percentage": value += 35
            if "co-pay" in evidence or "copay" in evidence or "co payment" in evidence: value += 25
            if any(token in evidence for token in ["age", "zone", "treatment", "hospital"]): value += 10
            return value
        return sorted(candidates, key=score, reverse=True)[0]
