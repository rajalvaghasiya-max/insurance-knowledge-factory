import re
import hashlib
from datetime import datetime, timezone
from collections import defaultdict

from config.settings import BASE_DIR
from storage.registry_store import load_json, save_json


class ProductConsolidationAgent:
    """
    Product Consolidation Agent v0.2

    Converts product signal files into canonical product-level records.

    Quality rules:
    - Only uses page_intent = individual_product
    - Only uses signals with product_names
    - Keeps source URLs and evidence
    - Removes noisy/navigation/premium-only pseudo benefit records
    """

    VERSION = "0.2"

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def consolidate_all(self) -> dict:
        signals_dir = BASE_DIR / "signals" / "product_signals"
        output_dir = BASE_DIR / "knowledge_domains" / "product" / "product_master"
        output_dir.mkdir(parents=True, exist_ok=True)

        if not signals_dir.exists():
            return {
                "status": "failed",
                "reason": f"Signals directory not found: {signals_dir}",
            }

        product_groups = defaultdict(list)
        total_files = 0
        eligible_files = 0
        skipped_files = 0

        for insurer_folder in signals_dir.iterdir():
            if not insurer_folder.is_dir():
                continue

            for signal_file in insurer_folder.glob("*.json"):
                total_files += 1
                signal = load_json(signal_file, default={})

                if not self.is_eligible_signal(signal):
                    skipped_files += 1
                    continue

                eligible_files += 1
                insurer_id = signal.get("insurer_id", "unknown")
                product_name = self.get_primary_product_name(signal)

                product_key = self.build_product_key(
                    insurer_id=insurer_id,
                    product_name=product_name,
                )

                product_groups[product_key].append(signal)

        product_records = []

        for product_key, signals in product_groups.items():
            product_record = self.build_product_record(product_key, signals)
            product_records.append(product_record)

            output_path = output_dir / f"{product_record['product_id']}.json"
            save_json(output_path, product_record)

        index_record = {
            "generated_at": self.utc_now_iso(),
            "agent": "product_consolidation_agent",
            "agent_version": self.VERSION,
            "total_signal_files": total_files,
            "eligible_signal_files": eligible_files,
            "skipped_signal_files": skipped_files,
            "product_count": len(product_records),
            "products": [
                {
                    "product_id": item["product_id"],
                    "insurer_id": item["insurer_id"],
                    "product_name": item["product_name"],
                    "source_count": len(item["source_urls"]),
                    "quality_confidence": item["quality"]["confidence"],
                    "benefit_count": len(item["benefits"]),
                    "exclusion_count": len(item["exclusions"]),
                    "waiting_period_count": len(item["waiting_periods"]),
                    "removed_noise_items": item["quality"]["removed_noise_items"],
                }
                for item in product_records
            ],
        }

        save_json(output_dir / "_product_master_index.json", index_record)

        return {
            "status": "completed",
            "total_signal_files": total_files,
            "eligible_signal_files": eligible_files,
            "skipped_signal_files": skipped_files,
            "product_count": len(product_records),
            "output_dir": str(output_dir),
        }

    def is_eligible_signal(self, signal: dict) -> bool:
        return signal.get("page_intent") == "individual_product" and bool(signal.get("product_names"))

    def get_primary_product_name(self, signal: dict) -> str:
        product_names = signal.get("product_names", [])
        if not product_names:
            return "Unknown Product"

        first = product_names[0]
        if isinstance(first, dict):
            return first.get("name", "Unknown Product").strip()

        return str(first).strip()

    def build_product_key(self, insurer_id: str, product_name: str) -> str:
        return f"{insurer_id}::{self.slugify(product_name)}"

    def build_product_id(self, insurer_id: str, product_name: str) -> str:
        base = f"{insurer_id}_{self.slugify(product_name)}"
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:10]
        return f"{base}_{digest}"

    def build_product_record(self, product_key: str, signals: list[dict]) -> dict:
        first_signal = signals[0]
        insurer_id = first_signal.get("insurer_id", "unknown")
        product_name = self.get_primary_product_name(first_signal)

        product_id = self.build_product_id(
            insurer_id=insurer_id,
            product_name=product_name,
        )

        record = {
            "product_id": product_id,
            "insurer_id": insurer_id,
            "product_name": product_name,
            "product_key": product_key,
            "status": "draft",
            "created_at": self.utc_now_iso(),
            "updated_at": self.utc_now_iso(),
            "consolidated_by": "product_consolidation_agent",
            "consolidator_version": self.VERSION,

            "source_urls": [],
            "source_content_hashes": [],
            "source_signal_files": [],

            "uins": [],
            "benefits": [],
            "exclusions": [],
            "waiting_periods": [],
            "riders_or_addons": [],
            "room_rent_limits": [],
            "claim_process_signals": [],
            "tax_signals": [],
            "suitability_signals": [],

            "financial_signals": {
                "sum_insured_values": [],
                "premium_values": [],
                "benefit_amount_values": [],
                "tax_amount_values": [],
                "discount_values": [],
            },

            "quality": {
                "source_count": len(signals),
                "has_uin": False,
                "has_benefits": False,
                "has_exclusions": False,
                "has_waiting_periods": False,
                "confidence": "draft",
                "notes": [],
                "removed_noise_items": 0,
            },
        }

        for signal in signals:
            self.merge_signal_into_record(record, signal)

        record["source_urls"] = sorted(set(record["source_urls"]))
        record["source_content_hashes"] = sorted(set(record["source_content_hashes"]))
        record["source_signal_files"] = sorted(set(record["source_signal_files"]))
        record["uins"] = sorted(set(record["uins"]))

        self.clean_record_signal_lists(record)

        record["quality"]["has_uin"] = len(record["uins"]) > 0
        record["quality"]["has_benefits"] = len(record["benefits"]) > 0
        record["quality"]["has_exclusions"] = len(record["exclusions"]) > 0
        record["quality"]["has_waiting_periods"] = len(record["waiting_periods"]) > 0
        record["quality"]["confidence"] = self.assign_confidence(record)

        return record

    def merge_signal_into_record(self, record: dict, signal: dict) -> None:
        url = signal.get("url")
        content_hash = signal.get("content_hash")
        source_file = signal.get("source_parsed_file")

        if url:
            record["source_urls"].append(url)
        if content_hash:
            record["source_content_hashes"].append(content_hash)
        if source_file:
            record["source_signal_files"].append(source_file)

        record["uins"].extend(signal.get("uins", []))

        signal_keys = [
            "benefits",
            "exclusions",
            "waiting_periods",
            "riders_or_addons",
            "room_rent_limits",
            "claim_process_signals",
            "tax_signals",
            "suitability_signals",
        ]

        for key in signal_keys:
            record[key].extend(self.add_source_to_items(signal.get(key, []), signal))

        financial_keys = [
            "sum_insured_values",
            "premium_values",
            "benefit_amount_values",
            "tax_amount_values",
            "discount_values",
        ]

        for key in financial_keys:
            record["financial_signals"][key].extend(
                self.add_source_to_items(signal.get(key, []), signal)
            )

    def add_source_to_items(self, items: list, signal: dict) -> list[dict]:
        enriched = []

        for item in items:
            if isinstance(item, dict):
                enriched_item = dict(item)
            else:
                enriched_item = {
                    "value": item,
                    "evidence": str(item),
                }

            enriched_item["source"] = {
                "url": signal.get("url"),
                "page_title": signal.get("page_title"),
                "content_hash": signal.get("content_hash"),
                "source_parsed_file": signal.get("source_parsed_file"),
                "extractor_version": signal.get("extractor_version"),
            }

            enriched.append(enriched_item)

        return enriched

    def clean_record_signal_lists(self, record: dict) -> None:
        top_level_keys = [
            "benefits",
            "exclusions",
            "waiting_periods",
            "riders_or_addons",
            "room_rent_limits",
            "claim_process_signals",
            "tax_signals",
            "suitability_signals",
        ]

        for key in top_level_keys:
            before = len(record[key])
            record[key] = self.filter_noise_items(record[key], key)
            record[key] = self.dedupe_signal_list(record[key])
            after = len(record[key])
            record["quality"]["removed_noise_items"] += max(0, before - after)

        for key in record["financial_signals"]:
            before = len(record["financial_signals"][key])
            record["financial_signals"][key] = self.filter_noise_items(
                record["financial_signals"][key],
                key,
            )
            record["financial_signals"][key] = self.dedupe_signal_list(
                record["financial_signals"][key]
            )
            after = len(record["financial_signals"][key])
            record["quality"]["removed_noise_items"] += max(0, before - after)

    def filter_noise_items(self, items: list[dict], bucket: str) -> list[dict]:
        return [item for item in items if not self.is_noise_item(item, bucket)]

    def is_noise_item(self, item: dict, bucket: str) -> bool:
        heading = str(item.get("heading", "")).strip()
        text = str(item.get("text", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        value = str(item.get("value", "")).strip()

        combined = f"{heading}\n{text}\n{evidence}\n{value}".lower()
        compact = re.sub(r"\s+", " ", combined).strip()

        hard_noise_phrases = [
            "products personal commercial msme",
            "personal commercial msme",
            "weather insurance rwbcis",
            "tools and locator",
            "view details",
            "know more",
            "read more",
            "get secure herizon",
            "select suitable coverage",
            "check discounts & offers",
            "buy comprehensive coverages",
            "receive instant policy confirmation",
            "secure payment",
            "enter personal details",
            "callback",
            "download app",
            "scan to download",
            "login",
            "logout",
            "sign in",
            "no yes all webpages",
        ]

        if any(phrase in compact for phrase in hard_noise_phrases):
            return True

        if bucket == "benefits":
            if self.is_premium_only_item(heading, text, evidence):
                return True

            if self.is_too_short_weak_item(heading, text, min_total_chars=45):
                return True

        if bucket in {"exclusions", "waiting_periods", "claim_process_signals"}:
            if self.is_too_short_weak_item(heading, text, min_total_chars=30):
                return True

        return False

    def is_premium_only_item(self, heading: str, text: str, evidence: str) -> bool:
        combined = f"{heading}\n{text}\n{evidence}".lower()

        money_or_premium_markers = [
            "/annum",
            "annum",
            "premium",
            "₹",
            "rs.",
            "rs ",
            "inr ",
        ]

        benefit_markers = [
            "cover",
            "covered",
            "coverage",
            "hospital",
            "hospitalisation",
            "hospitalization",
            "treatment",
            "claim",
            "sum insured",
            "room rent",
            "ambulance",
            "maternity",
            "day care",
            "opd",
            "ayush",
            "organ donor",
            "waiting period",
            "waiver",
            "reload",
            "reinstatement",
        ]

        has_money = any(marker in combined for marker in money_or_premium_markers)
        has_benefit = any(marker in combined for marker in benefit_markers)

        if has_money and not has_benefit:
            return True

        if "/annum" in combined and len(text.split()) <= 4:
            return True

        return False

    def is_too_short_weak_item(self, heading: str, text: str, min_total_chars: int) -> bool:
        combined = f"{heading} {text}".strip()
        words = combined.split()

        if len(combined) < min_total_chars:
            return True

        if len(words) <= 4:
            return True

        weak_headings = {
            "cover",
            "note",
            "not covered",
            "covered",
            "comprehensive",
            "hospitalization cover for",
            "for continuous coverage",
        }

        if heading.lower().strip(" :") in weak_headings and len(text.split()) <= 6:
            return True

        return False

    def dedupe_signal_list(self, items: list[dict]) -> list[dict]:
        seen = set()
        unique = []

        for item in items:
            marker = self.build_item_marker(item)
            if marker in seen:
                continue

            seen.add(marker)
            unique.append(item)

        return unique

    def build_item_marker(self, item: dict) -> str:
        value = str(item.get("value", "")).lower().strip()
        heading = str(item.get("heading", "")).lower().strip()
        text = str(item.get("text", "")).lower().strip()
        evidence = str(item.get("evidence", "")).lower().strip()

        return f"{value}|{heading}|{text[:250]}|{evidence[:250]}"

    def assign_confidence(self, record: dict) -> str:
        score = 0

        if record["quality"]["has_uin"]:
            score += 3
        if record["quality"]["has_benefits"]:
            score += 2
        if record["quality"]["has_exclusions"]:
            score += 2
        if record["quality"]["has_waiting_periods"]:
            score += 2
        if len(record["source_urls"]) >= 2:
            score += 1

        if score >= 8:
            return "high"
        if score >= 5:
            return "medium"
        return "low"

    def slugify(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text)
        return text.strip("_")
