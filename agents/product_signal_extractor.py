import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

from storage.registry_store import load_json, save_json
from config.settings import BASE_DIR
from agents.source_asset_classifier import SourceAssetClassifier
from agents.uin_candidate_extractor import UinCandidateExtractor


class ProductSignalExtractor:
    """
    Product Signal Extractor v0.8

    Quality improvements:
    - Stronger page_intent precedence
    - Customer service / homepage / FAQ / calculator excluded from product naming
    - Individual product detection based mainly on URL slug
    - Separates premium_values from sum_insured_values
    - Separates benefit_amount_values, tax_amount_values, discount_values
    - Extracts financial values using context gates
    - Extracts financial values only for individual_product pages
    - Adds per-value evidence for auditability
    - Uses stricter SI validation to reduce small payout/tax/premium leakage
    - Filters premium values to current product context to avoid cross-sell card leakage
    """

    VERSION = "0.8"

    def __init__(
        self,
        classifier: SourceAssetClassifier | None = None,
        uin_candidate_extractor: UinCandidateExtractor | None = None,
    ) -> None:
        self.classifier = classifier or SourceAssetClassifier()
        self.uin_candidate_extractor = uin_candidate_extractor or UinCandidateExtractor()

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def extract_from_parsed_file(self, parsed_file: Path) -> dict:
        parsed = load_json(parsed_file, default={})
        sections = parsed.get("sections", [])

        url = parsed.get("url", "") or ""
        page_title = parsed.get("page_title", "") or ""

        classification = self.classify_source_asset(url, page_title)
        page_intent = classification["page_intent"]

        signals = {
            "extractor_version": self.VERSION,
            "source_parsed_file": str(parsed_file),
            "insurer_id": parsed.get("insurer_id"),
            "url": url,
            "page_title": page_title,
            "content_hash": parsed.get("content_hash"),
            "page_intent": page_intent,
            "asset_scope": classification["asset_scope"],
            "classification_reason": classification["classification_reason"],
            "classification_rules_version": classification["classification_rules_version"],
            "extracted_at": self.utc_now_iso(),
            "product_names": [],
            "uins": [],
            "uin_candidates": [],
            "benefits": [],
            "exclusions": [],
            "waiting_periods": [],
            "riders_or_addons": [],
            "sum_insured_values": [],
            "premium_values": [],
            "benefit_amount_values": [],
            "tax_amount_values": [],
            "discount_values": [],
            "room_rent_limits": [],
            "claim_process_signals": [],
            "tax_signals": [],
            "suitability_signals": [],
        }

        signals["uin_candidates"] = self.extract_uin_candidates_from_sections(
            sections=sections,
            source_context={
                "source_parsed_file": str(parsed_file),
                "insurer_id": signals["insurer_id"],
                "url": url,
                "content_hash": signals["content_hash"],
            },
        )
        signals["uins"] = sorted(
            {candidate["uin"] for candidate in signals["uin_candidates"]}
        )

        product_name = self.extract_product_name_from_page(
            page_title=page_title,
            url=url,
            sections=sections,
            page_intent=page_intent,
        )

        if product_name:
            signals["product_names"].append(product_name)

        current_product_name = product_name.get("name") if product_name else ""

        financial_values = self.extract_financial_values(
            sections=sections,
            page_intent=page_intent,
            current_product_name=current_product_name,
        )
        signals["sum_insured_values"] = financial_values["sum_insured_values"]
        signals["premium_values"] = financial_values["premium_values"]
        signals["benefit_amount_values"] = financial_values["benefit_amount_values"]
        signals["tax_amount_values"] = financial_values["tax_amount_values"]
        signals["discount_values"] = financial_values["discount_values"]

        for section in sections:
            heading = section.get("heading", "").strip()
            text = section.get("text", "").strip()

            if self.is_navigation_or_noise(heading, text):
                continue

            if self.is_benefit_section(heading, text):
                signals["benefits"].append(self.make_signal(heading, text))

            if self.is_exclusion_section(heading, text):
                signals["exclusions"].append(self.make_signal(heading, text))

            if self.is_waiting_period_section(heading, text):
                signals["waiting_periods"].append(self.make_signal(heading, text))

            if self.is_rider_or_addon_section(heading, text):
                signals["riders_or_addons"].append(self.make_signal(heading, text))

            if self.is_room_rent_section(heading, text):
                signals["room_rent_limits"].append(self.make_signal(heading, text))

            if self.is_claim_section(heading, text):
                signals["claim_process_signals"].append(self.make_signal(heading, text))

            if self.is_tax_section(heading, text):
                signals["tax_signals"].append(self.make_signal(heading, text))

            if self.is_suitability_section(heading, text):
                signals["suitability_signals"].append(self.make_signal(heading, text))

        signals = self.dedupe_signals(signals)
        output_path = self.save_signals(signals)

        return {
            "status": "extracted",
            "insurer_id": signals["insurer_id"],
            "url": signals["url"],
            "page_intent": page_intent,
            "asset_scope": signals["asset_scope"],
            "output_path": str(output_path),
            "product_names": len(signals["product_names"]),
            "uins": len(signals["uins"]),
            "uin_candidates": len(signals["uin_candidates"]),
            "benefits": len(signals["benefits"]),
            "exclusions": len(signals["exclusions"]),
            "waiting_periods": len(signals["waiting_periods"]),
            "riders_or_addons": len(signals["riders_or_addons"]),
            "sum_insured_values": len(signals["sum_insured_values"]),
            "premium_values": len(signals["premium_values"]),
            "benefit_amount_values": len(signals["benefit_amount_values"]),
            "tax_amount_values": len(signals["tax_amount_values"]),
            "discount_values": len(signals["discount_values"]),
        }

    def classify_source_asset(self, url: str, page_title: str) -> dict[str, str]:
        return self.classifier.classify(url=url, page_title=page_title)

    def detect_page_intent(self, url: str, page_title: str) -> str:
        """Compatibility wrapper for callers that only need page intent."""
        return self.classify_source_asset(url, page_title)["page_intent"]

    def is_known_individual_product_slug(self, slug: str, url: str) -> bool:
        classification = self.classify_source_asset(url, "")
        return classification["page_intent"] == "individual_product"

    def extract_product_name_from_page(self, page_title: str, url: str, sections: list[dict], page_intent: str) -> dict | None:
        if page_intent not in {"individual_product", "article_or_product_related"}:
            return None

        slug_name = self.product_name_from_url(url)
        if slug_name and self.is_valid_product_name(slug_name):
            return {"name": slug_name, "source": "url_slug", "evidence": url}

        candidate = self.clean_product_title(page_title)
        if candidate and self.is_valid_product_name(candidate):
            return {"name": candidate, "source": "page_title", "evidence": page_title}

        for section in sections[:12]:
            heading = section.get("heading", "").strip()
            text = section.get("text", "").strip()
            if self.is_navigation_or_noise(heading, text):
                continue
            if self.is_valid_product_name(heading):
                return {"name": heading, "source": "section_heading", "evidence": text[:300]}
        return None

    def clean_product_title(self, title: str) -> str:
        if not title:
            return ""
        clean = title.strip()
        remove_phrases = [
            "buy", "online", "best price", "gst free", "fast claim settlement",
            "coverage & benefits", "aditya birla health insurance |", "| bajaj general",
            "| hdfc life", "in india 2026", "in india", "@₹15/day*", "@ best price", "@",
        ]
        for phrase in remove_phrases:
            clean = re.sub(re.escape(phrase), "", clean, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", clean).strip(" -|:@")

    def product_name_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        slug = path.split("/")[-1]
        query = parsed.query.lower()
        if "activonemaxplus" in query or "activ-one-max-plus" in query:
            return "Activ One Max Plus"
        if "activonemax" in query or "activ-one-max" in query:
            return "Activ One Max"
        if not slug:
            return ""
        slug = slug.replace(".html", "").replace("-", " ").replace("_", " ")
        cleanup_map = {
            "health insurance for senior citizens": "Senior Citizen Health Insurance",
            "individual health insurance plans": "Individual Health Insurance",
            "family health insurance india": "Family Health Insurance",
            "international health insurance": "International Health Insurance",
            "arogya sanjeevani standard health insurance policy": "Arogya Sanjeevani Health Insurance Policy",
            "health guard insurance policy": "Health Guard Insurance Policy",
            "my health care plan": "My Health Care Plan",
            "activ yuva homepage": "Activ Yuva",
        }
        normalized = slug.lower().strip()
        return cleanup_map.get(normalized, slug.title().strip())

    def is_valid_product_name(self, name: str) -> bool:
        if not name:
            return False
        lower = name.lower().strip()
        invalid_phrases = [
            "crop insurance", "commercial and msme", "tools and locator", "products",
            "personal", "commercial", "msme", "customer service", "download abcd",
            "receive plan benefits", "view details", "know more", "read more",
            "calculator", "faq", "faqs", "homepage", "home",
        ]
        if any(phrase in lower for phrase in invalid_phrases):
            return False
        if len(name) < 4 or len(name) > 90:
            return False
        product_words = [
            "insurance", "policy", "plan", "health", "term", "life", "activ", "arogya",
            "sanjeevani", "guard", "care", "yuva", "senior", "family", "global", "sanchay", "jeevan",
        ]
        return any(word in lower for word in product_words)

    def extract_financial_values(self, sections: list[dict], page_intent: str, current_product_name: str = "") -> dict:
        """
        Extract auditable financial signals.

        v0.7 quality gate:
        - Financial values are extracted only for individual_product pages.
        - Homepage / FAQ / calculator / customer service / article / listing pages are skipped.
        - Each value carries heading + evidence so we can review why it was captured.
        - Premium values are kept only when the evidence belongs to the current product.
        """
        result = {
            "sum_insured_values": [],
            "premium_values": [],
            "benefit_amount_values": [],
            "tax_amount_values": [],
            "discount_values": [],
        }

        seen = {key: set() for key in result}

        if page_intent != "individual_product":
            return result

        for section in sections:
            heading = section.get("heading", "")
            text = section.get("text", "")
            combined = f"{heading}\n{text}".strip()
            lower = combined.lower()
            heading_lower = heading.lower()

            money_values = self.extract_money_values(combined)
            percent_values = self.extract_percent_values(combined)

            if not money_values and not percent_values:
                continue

            # Precedence matters. Tax and discount sections often contain words like premium.
            if self.is_discount_context(lower):
                for value in money_values + percent_values:
                    self.add_financial_signal(
                        result, seen, "discount_values", value, heading, text, "discount_context"
                    )
                continue

            if self.is_tax_context(lower):
                for value in money_values + percent_values:
                    self.add_financial_signal(
                        result, seen, "tax_amount_values", value, heading, text, "tax_context"
                    )
                continue

            if self.is_sum_insured_context(lower):
                for value in money_values:
                    if self.is_valid_sum_insured_value(value, lower, heading_lower):
                        self.add_financial_signal(
                            result, seen, "sum_insured_values", value, heading, text, "sum_insured_context"
                        )
                continue

            if self.is_premium_context(lower):
                if not self.is_premium_relevant_to_current_product(
                    combined_text=lower,
                    heading_text=heading_lower,
                    current_product_name=current_product_name,
                ):
                    continue

                for value in money_values:
                    self.add_financial_signal(
                        result,
                        seen,
                        "premium_values",
                        value,
                        heading,
                        text,
                        "premium_context_current_product",
                    )
                continue

            if self.is_benefit_amount_context(lower):
                for value in money_values:
                    self.add_financial_signal(
                        result, seen, "benefit_amount_values", value, heading, text, "benefit_amount_context"
                    )

        return result

    def add_financial_signal(
        self,
        result: dict,
        seen: dict,
        bucket: str,
        value: str,
        heading: str,
        text: str,
        reason: str,
    ) -> None:
        cleaned_value = value.strip()

        if not cleaned_value:
            return

        marker = (cleaned_value.lower(), heading.lower().strip(), reason)

        if marker in seen[bucket]:
            return

        seen[bucket].add(marker)

        result[bucket].append({
            "value": cleaned_value,
            "reason": reason,
            "heading": heading.strip(),
            "evidence": f"{heading}\n{text}".strip()[:700],
        })

    def is_valid_sum_insured_value(self, value: str, lower_text: str, heading_lower: str) -> bool:
        value_lower = value.lower()

        # Sum insured is normally expressed in lakh/lac/crore or equivalent USD ranges.
        large_unit_markers = ["lakh", "lakhs", "lac", "lacs", "cr", "crore", "crores", "million"]
        if any(marker in value_lower for marker in large_unit_markers):
            return True

        if "usd" in value_lower:
            return True

        # Allow rupee values like INR 50,000 only when heading is explicitly SI-focused.
        explicit_si_heading = any(
            marker in heading_lower
            for marker in [
                "sum insured",
                "hospital & day care si",
                "hospitalisation si",
                "hospitalization si",
                "day care si",
            ]
        )

        if not explicit_si_heading:
            return False

        numeric_value = self.extract_numeric_amount(value)
        return numeric_value is not None and numeric_value >= 50000

    def extract_numeric_amount(self, value: str) -> float | None:
        match = re.search(r"[0-9][0-9,.]*", value)
        if not match:
            return None

        try:
            return float(match.group(0).replace(",", ""))
        except ValueError:
            return None

    def extract_uins(self, text: str) -> list[str]:
        """Compatibility helper returning values from shared candidate extraction."""
        return sorted(
            {
                candidate["uin"]
                for candidate in self.uin_candidate_extractor.extract(text)
            }
        )

    def extract_uin_candidates_from_sections(
        self,
        *,
        sections: list[dict],
        source_context: dict,
    ) -> list[dict]:
        """Extract candidates with section-local provenance for later identity resolution."""
        candidates: list[dict] = []

        for section_index, section in enumerate(sections):
            heading = str(section.get("heading", "")).strip()
            text = str(section.get("text", "")).strip()
            section_text = "\n".join(part for part in (heading, text) if part)
            if not section_text:
                continue

            context = {
                **source_context,
                "section_index": section_index,
                "section_heading": heading or None,
            }
            candidates.extend(
                self.uin_candidate_extractor.extract(
                    section_text,
                    source=context,
                )
            )

        return candidates

    def extract_money_values(self, text: str) -> list[str]:
        patterns = [
            r"\bINR\s?[0-9][0-9,.]*\s?(?:thousand|lakh|lakhs|lac|lacs|cr|crore|crores)?\b",
            r"\bRs\.?\s?[0-9][0-9,.]*\s?(?:thousand|lakh|lakhs|lac|lacs|cr|crore|crores)?\b",
            r"₹\s?[0-9][0-9,.]*\s?(?:thousand|lakh|lakhs|lac|lacs|cr|crore|crores)?\b",
            r"\bUSD\s?[0-9][0-9,.]*\s?(?:thousand|lakh|lac|million)?\b",
        ]
        found = set()
        for pattern in patterns:
            for match in re.findall(pattern, text, flags=re.IGNORECASE):
                cleaned = match.strip().rstrip(".,;:*")
                if cleaned.lower() in ["rs", "rs.", "inr", "₹", "usd"]:
                    continue
                if not re.search(r"\d", cleaned):
                    continue
                found.add(cleaned)
        return sorted(found)

    def extract_percent_values(self, text: str) -> list[str]:
        return sorted(set(re.findall(r"\b[0-9]{1,3}(?:\.[0-9]+)?\s?%\b", text)))

    def is_sum_insured_context(self, text: str) -> bool:
        positive = ["sum insured", "sum-insured", " si ", "hospital & day care si", "hospitalisation si", "hospitalization si", "base sum insured", "coverage amount", "cover amount", "coverage limit"]
        negative = ["premium", "discount", "tax", "deduction", "starting from", "+ gst", "per annum", "/annum", "daily cash", "hospital cash", "claim-free", "no claim bonus", "cumulative bonus"]
        return any(k in text for k in positive) and not any(k in text for k in negative)

    def is_premium_context(self, text: str) -> bool:
        return any(k in text for k in ["premium", "annum", "/annum", "per annum", "starting from", "+ gst", "pay annually", "premium payment"])

    def is_premium_relevant_to_current_product(
        self,
        combined_text: str,
        heading_text: str,
        current_product_name: str,
    ) -> bool:
        """
        Prevent cross-sell product cards from leaking premium values.

        Keep premium values only when the surrounding evidence clearly belongs
        to the current product page's detected product name.
        """
        if not current_product_name:
            return False

        normalized_product = self.normalize_for_match(current_product_name)
        normalized_combined = self.normalize_for_match(combined_text)
        normalized_heading = self.normalize_for_match(heading_text)

        if not normalized_product:
            return False

        # Strongest signal: full product name appears in evidence or heading.
        if normalized_product in normalized_combined or normalized_product in normalized_heading:
            return True

        product_tokens = self.distinctive_product_tokens(current_product_name)

        if not product_tokens:
            return False

        # For short product names like Activ Yuva, require all distinctive tokens.
        if all(token in normalized_combined for token in product_tokens):
            return True

        return False

    def normalize_for_match(self, value: str) -> str:
        value = value.lower()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    def distinctive_product_tokens(self, product_name: str) -> list[str]:
        generic_tokens = {
            "insurance",
            "policy",
            "plan",
            "health",
            "life",
            "general",
            "online",
            "buy",
            "coverage",
            "benefits",
            "india",
            "senior",
            "citizen",
            "family",
            "individual",
        }

        tokens = self.normalize_for_match(product_name).split()
        return [token for token in tokens if token not in generic_tokens and len(token) >= 3]

    def is_tax_context(self, text: str) -> bool:
        return any(k in text for k in ["tax", "80c", "80d", "10(10d)", "deduction", "income tax", "tax benefit", "tax saving"])

    def is_discount_context(self, text: str) -> bool:
        return any(k in text for k in ["discount", "online discount", "zone discount", "direct discount", "long-term policy discount", "family discount", "employee discount"])

    def is_benefit_amount_context(self, text: str) -> bool:
        return any(k in text for k in ["daily cash", "hospital cash", "road ambulance", "air ambulance", "convalescence", "preventive check", "health check", "home nursing", "organ donor", "maternity sublimit", "baby care", "opd cover", "claim amount", "benefit payout", "allowance"])

    def is_navigation_or_noise(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower().strip()
        noise_phrases = [
            "products personal commercial msme", "weather insurance rwbcis", "commercial and msme insurance claim",
            "tools and locator", "support customer service", "you want to delete from wishlist",
            "this action will permanently delete", "download app", "login", "logout", "sign in", "view details",
            "know more", "read more", "back eng english", "submit", "callback", "enter personal details",
            "secure payment", "receive instant policy confirmation", "no yes all webpages",
        ]
        if any(phrase in combined for phrase in noise_phrases):
            return True
        return len(combined.split()) <= 3

    def join_sections(self, sections: list[dict]) -> str:
        parts = []
        for section in sections:
            parts.append(section.get("heading", ""))
            parts.append(section.get("text", ""))
        return "\n".join(parts)

    def make_signal(self, heading: str, text: str) -> dict:
        return {"heading": heading.strip(), "text": text.strip(), "evidence": f"{heading}\n{text}".strip()[:1000]}

    def is_benefit_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower()
        keywords = ["benefit", "covered", "coverage", "inclusion", "hospitalisation", "hospitalization", "day care", "ambulance", "organ donor", "ayush", "maternity", "newborn", "reinstatement", "cumulative bonus", "health check", "opd", "domiciliary"]
        return any(keyword in combined for keyword in keywords)

    def is_exclusion_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower()
        keywords = ["exclusion", "not covered", "excluded", "self-inflicted", "dietary supplements", "cosmetic surgery", "investigation", "evaluation", "hazardous", "intoxication"]
        return any(keyword in combined for keyword in keywords)

    def is_waiting_period_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower()
        keywords = ["waiting period", "initial waiting", "pre-existing", "ped", "specific illness", "specific disease", "30 days", "24 months", "36 months", "48 months", "72 months"]
        return any(keyword in combined for keyword in keywords)

    def is_rider_or_addon_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower()
        keywords = ["rider", "add-on", "addon", "additional cover", "optional", "waiver", "personal accident cover", "non-medical expense", "respect rider", "health prime", "room capping waiver"]
        return any(keyword in combined for keyword in keywords)

    def is_room_rent_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower()
        keywords = ["room rent", "room limit", "room limits", "single private", "icu", "room capping"]
        return any(keyword in combined for keyword in keywords)

    def is_claim_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower()
        keywords = ["claim", "cashless", "reimbursement", "documents", "pre-authorization", "hospitalization claim", "settlement"]
        return any(keyword in combined for keyword in keywords)

    def is_tax_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower()
        keywords = ["tax", "80c", "80d", "10(10d)", "deduction", "income tax"]
        return any(keyword in combined for keyword in keywords)

    def is_suitability_section(self, heading: str, text: str) -> bool:
        combined = f"{heading} {text}".lower()
        keywords = ["suitable", "for women", "for family", "senior citizen", "young", "children", "retirement", "nri", "self employed", "doctors", "housewife", "parents", "family floater"]
        return any(keyword in combined for keyword in keywords)

    def dedupe_signals(self, signals: dict) -> dict:
        signal_keys = ["product_names", "benefits", "exclusions", "waiting_periods", "riders_or_addons", "room_rent_limits", "claim_process_signals", "tax_signals", "suitability_signals"]
        for key in signal_keys:
            seen = set()
            unique = []
            for item in signals.get(key, []):
                marker = (item.get("name", item.get("heading", "")).lower().strip(), item.get("text", item.get("evidence", "")).lower().strip()[:300])
                if marker not in seen:
                    seen.add(marker)
                    unique.append(item)
            signals[key] = unique
        candidates = signals.get("uin_candidates", [])
        seen_candidates = set()
        unique_candidates = []
        for candidate in candidates:
            source = candidate.get("source", {})
            marker = (
                candidate.get("uin"),
                source.get("source_parsed_file"),
                source.get("section_index"),
                candidate.get("match_start"),
            )
            if marker in seen_candidates:
                continue
            seen_candidates.add(marker)
            unique_candidates.append(candidate)
        signals["uin_candidates"] = unique_candidates
        signals["uins"] = sorted(
            {candidate.get("uin") for candidate in unique_candidates if candidate.get("uin")}
        )

        for financial_key in [
            "sum_insured_values",
            "premium_values",
            "benefit_amount_values",
            "tax_amount_values",
            "discount_values",
        ]:
            signals[financial_key] = self.dedupe_financial_signals(
                signals.get(financial_key, [])
            )

        return signals

    def dedupe_financial_signals(self, items: list[dict]) -> list[dict]:
        seen = set()
        unique = []

        for item in items:
            marker = (
                item.get("value", "").lower().strip(),
                item.get("heading", "").lower().strip(),
                item.get("reason", "").lower().strip(),
            )

            if marker in seen:
                continue

            seen.add(marker)
            unique.append(item)

        return sorted(
            unique,
            key=lambda item: (
                item.get("value", ""),
                item.get("heading", ""),
                item.get("reason", ""),
            ),
        )

    def save_signals(self, signals: dict) -> Path:
        insurer_id = signals.get("insurer_id", "unknown")
        content_hash = signals.get("content_hash", "unknown")
        output_dir = BASE_DIR / "signals" / "product_signals" / insurer_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{content_hash}.json"
        save_json(output_path, signals)
        return output_path
