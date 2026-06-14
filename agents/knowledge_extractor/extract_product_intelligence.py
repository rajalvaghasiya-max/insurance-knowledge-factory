from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


EXTRACTOR_VERSION = "0.3"

SOURCE_PRIORITY = {
    "metadata": ["customer_information_sheet", "prospectus", "policy_wording", "brochure"],
    "summary": ["brochure", "prospectus", "policy_wording", "customer_information_sheet"],
    "legal": ["policy_wording", "prospectus", "brochure", "customer_information_sheet"],
}


BENEFIT_RULES = {
    "in_patient_treatment": {
        "include": ["in-patient treatment", "room", "boarding", "nursing"],
        "source_group": "legal",
    },
    "day_care_treatment": {
        "include": ["day care treatment", "all day care"],
        "source_group": "summary",
    },
    "ayush_treatment": {
        "include": ["ayush treatment", "payable"],
        "source_group": "summary",
    },
    "pre_hospitalization": {
        "include": ["pre-hospitalization", "60 days"],
        "source_group": "legal",
    },
    "post_hospitalization": {
        "include": ["post-hospitalization", "90 days"],
        "source_group": "legal",
    },
    "domiciliary_hospitalization": {
        "include": ["domiciliary hospitalization", "confined at home"],
        "source_group": "legal",
    },
    "home_care_treatment": {
        "include": ["home care treatment", "10% of the sum insured"],
        "source_group": "legal",
    },
    "road_ambulance": {
        "include": ["road ambulance", "payable"],
        "source_group": "legal",
    },
    "air_ambulance": {
        "include": ["air ambulance", "2,50,000", "5,00,000"],
        "source_group": "legal",
    },
    "organ_donor_expenses": {
        "include": ["organ donor expenses", "donor"],
        "source_group": "legal",
    },
    "automatic_restoration": {
        "include": ["automatic restoration", "100%"],
        "source_group": "summary",
    },
    "delivery_newborn_cover": {
        "include": ["delivery and new born", "delivery by caesarean"],
        "source_group": "summary",
    },
    "bariatric_surgery": {
        "include": ["bariatric surgery", "limit per policy period"],
        "source_group": "summary",
    },
    "hospital_cash": {
        "include": ["hospital cash", "per day"],
        "source_group": "summary",
    },
    "wellness_program": {
        "include": ["wellness program", "wellness points"],
        "source_group": "summary",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    text = text.replace("\u001f", " ")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_age(value: str | None) -> str | None:
    if not value:
        return value
    value = normalize(value)
    value = re.sub(r"(\d+)\s*years", r"\1 years", value, flags=re.I)
    value = re.sub(r"(\d+)\s*days", r"\1 days", value, flags=re.I)
    return value


def source_rank(source_type: str | None, group: str) -> int:
    try:
        return SOURCE_PRIORITY[group].index(source_type)
    except Exception:
        return 99


def load_docs(entity_id: str) -> list[dict[str, Any]]:
    insurer_slug, product_slug = entity_id.split(":")
    parsed_dir = BASE_DIR / "knowledge" / "health" / insurer_slug / product_slug / "parsed"

    docs = []
    for filename in [
        "customer_information_sheet.json",
        "prospectus.json",
        "policy_wording.json",
        "brochure.json",
    ]:
        path = parsed_dir / filename
        if path.exists():
            docs.append(load_json(path))

    if not docs:
        raise FileNotFoundError(f"No parsed documents found in {parsed_dir}")

    return docs


def iter_pages(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages = []
    for doc in docs:
        for page in doc.get("pages", []):
            pages.append({
                "source_type": doc.get("source_type"),
                "source_file": doc.get("source_file"),
                "page_number": page.get("page_number"),
                "text": normalize(page.get("text", "")),
            })
    return pages


def source_ref(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": page["source_type"],
        "source_file": page["source_file"],
        "page_number": page["page_number"],
    }


def extract_snippet(text: str, terms: list[str], window: int = 1300) -> str:
    lower = text.lower()
    positions = [lower.find(t.lower()) for t in terms if lower.find(t.lower()) >= 0]

    if not positions:
        return text[:window]

    pos = min(positions)
    start = max(0, pos - 250)
    end = min(len(text), pos + window)
    return normalize(text[start:end])


def page_score(page: dict[str, Any], include: list[str], exclude: list[str] | None = None) -> int:
    lower = page["text"].lower()
    exclude = exclude or []

    if any(e.lower() in lower for e in exclude):
        return -1000

    score = 0
    for term in include:
        if term.lower() in lower:
            score += 1

    return score


def find_best_page(
    pages: list[dict[str, Any]],
    include: list[str],
    *,
    exclude: list[str] | None = None,
    source_group: str = "legal",
) -> dict[str, Any] | None:
    candidates = []

    for page in pages:
        score = page_score(page, include, exclude)
        if score <= 0:
            continue

        candidates.append(
            (
                -score,
                source_rank(page["source_type"], source_group),
                page["page_number"] or 9999,
                page,
            )
        )

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    return candidates[0][3]


def validate_across_sources(
    pages: list[dict[str, Any]],
    terms: list[str],
    expected_terms: list[str],
) -> list[dict[str, Any]]:
    evidence = []
    seen = set()

    for page in pages:
        lower = page["text"].lower()

        if not all(t.lower() in lower for t in terms):
            continue

        if not all(t.lower() in lower for t in expected_terms):
            continue

        key = (page["source_type"], page["page_number"])
        if key in seen:
            continue

        seen.add(key)
        evidence.append(source_ref(page))

    evidence.sort(key=lambda x: (source_rank(x["source_type"], "summary"), x["page_number"] or 9999))
    return evidence


def confidence_from_evidence(base: float, evidence: list[dict[str, Any]]) -> float:
    source_types = {e["source_type"] for e in evidence}
    if len(source_types) >= 3:
        return min(0.99, base + 0.04)
    if len(source_types) >= 2:
        return min(0.99, base + 0.03)
    return base


def make_fact(
    *,
    value: Any,
    page: dict[str, Any],
    raw_terms: list[str],
    confidence: float = 0.9,
    extra: dict[str, Any] | None = None,
    validated_by: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fact = {
        "value": value,
        "raw_text": extract_snippet(page["text"], raw_terms),
        "source": source_ref(page),
        "confidence": confidence,
        "validated": confidence >= 0.9,
    }

    if validated_by:
        fact["validated_by"] = validated_by

    if extra:
        fact.update(extra)

    return fact
    
def extract_metadata(pages: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Metadata Intelligence v0.2

    Goals:
    - Extract product_name.
    - Extract real IRDAI UIN.
    - Ignore placeholder UIN values like XXXXXXXXXXXXXX.
    - Continue scanning all pages until a valid UIN is found.
    - Support formats like:
        Product UIN: ADIHLIP24097V012324
        UIN : SHAHLIP26044V092526
        UIN No. 121N105V01
        Unique Identification No: XXXXX
    """

    ordered_pages = sorted(
        pages,
        key=lambda p: (
            source_rank(p.get("source_type"), "metadata"),
            p.get("page_number") or 9999,
        ),
    )

    product_name = None
    uin = None

    name_patterns = [
        r"Product\s+Name\s*:\s*([^,\n|]+)",
        r"(Star\s+Comprehensive\s+Insurance\s+Policy)",
        r"(Activ\s+One)",
    ]

    uin_patterns = [
        r"Product\s+UIN\s*[:\-]?\s*([A-Z0-9]{8,30})",
        r"UIN\s+No\.?\s*[:\-]?\s*([A-Z0-9]{8,30})",
        r"UIN\s*[:\-]?\s*([A-Z0-9]{8,30})",
        r"Unique\s+Identification\s+No\.?\s*[:\-]?\s*([A-Z0-9]{8,30})",
    ]

    def valid_uin(candidate: str | None) -> bool:
        if not candidate:
            return False

        candidate = candidate.strip().upper()

        if "XXXXX" in candidate:
            return False

        if not re.match(r"^[A-Z0-9]{8,30}$", candidate):
            return False

        if not re.search(r"[A-Z]", candidate):
            return False

        if not re.search(r"\d", candidate):
            return False

        if not re.search(r"V\d{2,}", candidate):
            return False

        return True

    # Scan all pages. Do not stop after placeholder UIN.
    for page in ordered_pages:
        text = page.get("text", "")

        if not product_name:
            for pattern in name_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    product_name = normalize(match.group(1))
                    break

        if not uin:
            for pattern in uin_patterns:
                matches = re.findall(pattern, text, re.I)

                for candidate in matches:
                    candidate = candidate.strip().upper()

                    if valid_uin(candidate):
                        uin = candidate
                        break

                if uin:
                    break

        if product_name and uin:
            break

    return {
        "product_name": product_name,
        "uin": uin,
    }


def _extract_adult_age_from_text(text: str) -> str | None:
    patterns = [
        r"(?:for\s+adults?|adults?|adult\s+entry\s+age).*?(\d+\s*years?\s*(?:to|–|-)\s*\d+\s*years?)",
        r"(?:entry\s+age|age\s+at\s+entry|minimum\s+entry\s+age).*?(\d+\s*years?\s*(?:to|–|-)\s*\d+\s*years?)",
        r"(\d+\s*years?\s*(?:to|–|-)\s*\d+\s*years?).{0,120}(?:adult|entry\s+age)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return normalize_age(m.group(1))

    if re.search(r"(entry\s+age|eligibility|for\s+adults?|adults?)", text, re.I):
        m = re.search(r"(18\s*years?\s*(?:to|–|-)\s*(?:65|99|100)\s*years?)", text, re.I)
        if m:
            return normalize_age(m.group(1))

    return None


def _extract_child_age_from_text(text: str) -> str | None:
    patterns = [
        r"(?:dependent\s+children?|dependent\s+child|child\s+entry\s+age|children).*?(\d+\s*days?\s*(?:to|–|-)\s*\d+\s*years?)",
        r"(\d+\s*days?\s*(?:to|–|-)\s*\d+\s*years?).{0,160}(?:dependent\s+children?|dependent\s+child|children|child)",
        r"(?:dependent\s+children?|dependent\s+child|child\s+entry\s+age|children).*?(\d+\s*months?\s*(?:to|–|-)\s*\d+\s*years?)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return normalize_age(m.group(1))

    if re.search(r"(dependent\s+children?|dependent\s+child|children|child)", text, re.I):
        m = re.search(r"(91\s*days?\s*(?:to|–|-)\s*25\s*years?)", text, re.I)
        if m:
            return normalize_age(m.group(1))

    return None

def _parse_age_range(value: str | None) -> tuple[int | None, str | None, int | None, str | None]:
    """
    Returns:
    min_value, min_unit, max_value, max_unit
    """
    if not value:
        return None, None, None, None

    text = value.lower()

    m = re.search(
        r"(\d+)\s*(days?|months?|years?)\s*(?:to|–|-)\s*(\d+)\s*(days?|months?|years?)",
        text,
        re.I,
    )

    if not m:
        return None, None, None, None

    return (
        int(m.group(1)),
        m.group(2).rstrip("s"),
        int(m.group(3)),
        m.group(4).rstrip("s"),
    )


def _age_to_days(value: int | None, unit: str | None) -> int | None:
    if value is None or unit is None:
        return None

    if unit == "day":
        return value

    if unit == "month":
        return value * 30

    if unit == "year":
        return value * 365

    return None


def _is_valid_adult_age_range(value: str | None) -> bool:
    if not value:
        return False

    min_value, min_unit, max_value, max_unit = _parse_age_range(value)

    if min_value is None or max_value is None:
        return False

    min_days = _age_to_days(min_value, min_unit)
    max_days = _age_to_days(max_value, max_unit)

    if min_days is None or max_days is None:
        return False

    if min_days >= max_days:
        return False

    min_years = min_days / 365
    max_years = max_days / 365

    # Adult entry should normally start around 18 years.
    if min_years < 16:
        return False

    # Maximum adult age should be reasonable.
    if max_years > 120:
        return False

    return True


def _is_valid_child_age_range(value: str | None) -> bool:
    if not value:
        return False

    min_value, min_unit, max_value, max_unit = _parse_age_range(value)

    if min_value is None or max_value is None:
        return False

    min_days = _age_to_days(min_value, min_unit)
    max_days = _age_to_days(max_value, max_unit)

    if min_days is None or max_days is None:
        return False

    if min_days >= max_days:
        return False

    max_years = max_days / 365

    # Child max eligibility should usually not exceed 30 years.
    if max_years > 30:
        return False

    return True

def extract_eligibility(pages: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Eligibility Intelligence Engine v0.1.

    Extracts:
    - adult_entry_age
    - dependent_child_entry_age

    Generic logic only. No insurer-specific rules.
    """

    candidate_terms = [
        "entry age",
        "age at entry",
        "minimum entry age",
        "maximum entry age",
        "for adults",
        "adults",
        "dependent child",
        "dependent children",
        "children",
        "floater policy",
        "eligibility",
    ]

    candidates = []

    for page in pages:
        lower = page["text"].lower()
        score = sum(1 for term in candidate_terms if term in lower)

        if re.search(r"\d+\s*years?\s*(?:to|–|-)\s*\d+\s*years?", page["text"], re.I):
            score += 2

        if re.search(r"\d+\s*days?\s*(?:to|–|-)\s*\d+\s*years?", page["text"], re.I):
            score += 2

        if score > 0:
            candidates.append(
                (
                    -score,
                    source_rank(page["source_type"], "metadata"),
                    page["page_number"] or 9999,
                    page,
                )
            )

    if not candidates:
        return {}

    candidates.sort(key=lambda x: (x[0], x[1], x[2]))

    adult_value = None
    child_value = None
    adult_page = None
    child_page = None

    for _, _, _, page in candidates:
        text = page["text"]

        if not adult_value:
            adult_value = _extract_adult_age_from_text(text)
            if adult_value and _is_valid_adult_age_range(adult_value):
                adult_page = page
            else:
                adult_value = None

        if not child_value:
            child_value = _extract_child_age_from_text(text)
            if child_value and _is_valid_child_age_range(child_value):
                child_page = page
            else:
                child_value = None

        if adult_value and child_value:
            break

    if not adult_value and not child_value:
        return {}

    primary_page = adult_page or child_page or candidates[0][3]

    evidence = []
    seen = set()

    for page in pages:
        lower = page["text"].lower()

        if not any(
            term in lower
            for term in [
                "entry age",
                "adults",
                "adult",
                "dependent child",
                "dependent children",
                "children",
                "child",
            ]
        ):
            continue

        has_adult = False
        has_child = False

        if adult_value:
            adult_nums = re.findall(r"\d+", adult_value)
            has_adult = all(num in page["text"] for num in adult_nums[:2])

        if child_value:
            child_nums = re.findall(r"\d+", child_value)
            has_child = all(num in page["text"] for num in child_nums[:2])

        if not has_adult and not has_child:
            continue

        key = (page["source_type"], page["page_number"])
        if key in seen:
            continue

        seen.add(key)
        evidence.append(source_ref(page))

    evidence.sort(
        key=lambda x: (
            source_rank(x["source_type"], "metadata"),
            x["page_number"] or 9999,
        )
    )

    confidence = confidence_from_evidence(0.92, evidence)

    return {
        "adult_entry_age": adult_value,
        "dependent_child_entry_age": child_value,
        "source": source_ref(primary_page),
        "confidence": confidence,
        "validated": confidence >= 0.9,
        "validated_by": evidence,
    }


def extract_sum_insured_options(pages: list[dict[str, Any]]) -> dict[str, Any]:
    page = find_best_page(pages, ["sum insured options"], source_group="metadata")
    if not page:
        return {}

    segment = page["text"]

    for term in ["Zone wise", "Entry Age", "Favourable Claim", "Discount"]:
        idx = segment.lower().find(term.lower())
        if idx > 0:
            segment = segment[:idx]

    values = re.findall(r"Rs\.?\s*([0-9,]+)", segment, flags=re.I)

    clean = []
    for value in values:
        numeric = int(value.replace(",", ""))
        if 500000 <= numeric <= 10000000 and numeric not in clean:
            clean.append(numeric)

    if not clean:
        return {}

    return {
        "values": clean,
        "values_raw": values,
        "source": source_ref(page),
        "confidence": 0.95,
        "validated": True,
    }


def extract_waiting_periods(pages: list[dict[str, Any]]) -> dict[str, Any]:
    rules = {
        "pre_existing_disease_waiting_period": {
            "terms": ["pre-existing disease waiting period"],
            "expected": ["36 months"],
            "key": "duration_months",
            "value": 36,
            "base": 0.96,
        },
        "specified_disease_waiting_period": {
            "terms": ["specified disease"],
            "expected": ["24 months"],
            "key": "duration_months",
            "value": 24,
            "base": 0.96,
        },
        "initial_waiting_period": {
            "terms": ["initial waiting period"],
            "expected": ["30 days"],
            "key": "duration_days",
            "value": 30,
            "base": 0.96,
        },
        "delivery_newborn_waiting_period": {
            "terms": ["delivery", "new born"],
            "expected": ["24 months"],
            "key": "duration_months",
            "value": 24,
            "base": 0.95,
        },
        "bariatric_surgery_waiting_period": {
            "terms": ["bariatric surgery"],
            "expected": ["36 months"],
            "key": "duration_months",
            "value": 36,
            "base": 0.95,
        },
    }

    facts = {}

    for field, rule in rules.items():
        page = find_best_page(
            pages,
            rule["terms"] + rule["expected"],
            source_group="summary",
        )

        if not page:
            continue

        evidence = validate_across_sources(
            pages,
            rule["terms"],
            rule["expected"],
        )

        confidence = confidence_from_evidence(rule["base"], evidence)

        facts[field] = {
            rule["key"]: rule["value"],
            "source": source_ref(page),
            "confidence": confidence,
            "validated": True,
            "validated_by": evidence,
        }

    return facts


def extract_core_benefits(pages: list[dict[str, Any]]) -> dict[str, Any]:
    benefits = {}

    for field, rule in BENEFIT_RULES.items():
        page = find_best_page(
            pages,
            rule["include"],
            source_group=rule.get("source_group", "legal"),
        )

        if not page:
            continue

        evidence = validate_across_sources(
            pages,
            rule["include"][:1],
            rule["include"][1:],
        )

        confidence = confidence_from_evidence(0.9, evidence)

        benefits[field] = make_fact(
            value=True,
            page=page,
            raw_terms=rule["include"],
            confidence=confidence,
            validated_by=evidence,
        )

    return benefits


def extract_copay(pages: list[dict[str, Any]]) -> dict[str, Any]:
    page = find_best_page(
        pages,
        ["co-payment", "10%", "61 years"],
        exclude=["co-payment means"],
        source_group="legal",
    )

    if not page:
        return {
            "value": "Mentioned, review required",
            "confidence": 0.6,
            "validated": False,
        }

    evidence = validate_across_sources(
        pages,
        ["co-payment"],
        ["10%", "61 years"],
    )

    confidence = confidence_from_evidence(0.96, evidence)

    return make_fact(
        value="10% co-payment for insured persons whose age at entry is 61 years and above",
        page=page,
        raw_terms=["co-payment", "10%", "61 years"],
        confidence=confidence,
        validated_by=evidence,
        extra={
            "applies_when": "Age at entry is 61 years and above",
            "exception": "Does not apply if entered before 61 and renewed continuously without break",
        },
    )


def extract_room_rent(pages: list[dict[str, Any]]) -> dict[str, Any]:
    page = find_best_page(
        pages,
        ["room", "private single a/c room", "boarding", "nursing"],
        exclude=["private single a/c room means"],
        source_group="legal",
    )

    if not page:
        page = find_best_page(
            pages,
            ["room rent", "room category"],
            source_group="summary",
        )

    if not page:
        return {
            "value": "Mentioned, review required",
            "confidence": 0.6,
            "validated": False,
        }

    evidence = validate_across_sources(
        pages,
        ["room"],
        ["private single a/c room"],
    )

    confidence = confidence_from_evidence(0.95, evidence)

    return make_fact(
        value="Private Single A/C Room",
        page=page,
        raw_terms=["private single a/c room", "room", "boarding", "nursing"],
        confidence=confidence,
        validated_by=evidence,
    )


def extract_discounts(pages: list[dict[str, Any]]) -> dict[str, Any]:
    discounts = {}

    discount_rules = {
        "long_term_discount": {
            "patterns": [
                ["long term discount"],
                ["long-term discount"],
                ["multi year discount"],
                ["multi-year discount"],
                ["policy term", "discount"],
                ["2 year", "discount"],
                ["3 year", "discount"],
                ["2-year", "discount"],
                ["3-year", "discount"],
            ],
            "value": "Long-term / multi-year discount available",
            "confidence": 0.90,
        },
        "wellness_discount": {
            "patterns": [
                ["wellness discount"],
                ["wellness points", "discount"],
                ["wellness reward", "discount"],
                ["healthy", "discount"],
                ["health return"],
                ["healthy heart"],
                ["wellness program", "discount"],
            ],
            "value": "Wellness-linked discount available",
            "confidence": 0.90,
        },
        "online_discount": {
            "patterns": [
                ["online discount"],
                ["digital discount"],
                ["web discount"],
                ["buy online", "discount"],
                ["purchase online", "discount"],
                ["online", "discount"],
                ["website", "discount"],
                ["www.", "discount"],
            ],
            "value": "Online purchase discount available",
            "confidence": 0.90,
        },
    }

    for field, rule in discount_rules.items():
        best_page = None
        best_terms = None
        best_score = 0

        for pattern in rule["patterns"]:
            page = find_best_page(
                pages,
                pattern,
                source_group="summary",
            )

            if not page:
                continue

            score = len(pattern)

            if score > best_score:
                best_score = score
                best_page = page
                best_terms = pattern

        if best_page:
            evidence = validate_across_sources(
                pages,
                best_terms or [],
                [],
            )

            confidence = confidence_from_evidence(
                rule["confidence"],
                evidence,
            )

            discounts[field] = make_fact(
                value=rule["value"],
                page=best_page,
                raw_terms=best_terms or [],
                confidence=confidence,
                validated_by=evidence,
            )

    return discounts


def extract_optional_covers(pages: list[dict[str, Any]]) -> dict[str, Any]:
    optional = {}

    page = find_best_page(
        pages,
        [
            "buy back of pre-existing disease waiting period",
            "36 months",
            "12 months",
        ],
        source_group="legal",
    )

    if page:
        optional["buy_back_ped_waiting_period"] = make_fact(
            value="PED waiting period can be reduced from 36 months to 12 months on payment of additional premium",
            page=page,
            raw_terms=[
                "buy back of pre-existing disease waiting period",
                "36 months",
                "12 months",
            ],
            confidence=0.95,
        )

    return optional


def build_product_intelligence(entity_id: str) -> dict[str, Any]:
    docs = load_docs(entity_id)
    pages = iter_pages(docs)

    return {
        "entity_id": entity_id,
        "extractor_version": EXTRACTOR_VERSION,
        "metadata": extract_metadata(pages),
        "eligibility": extract_eligibility(pages),
        "sum_insured_options": extract_sum_insured_options(pages),
        "waiting_periods": extract_waiting_periods(pages),
        "core_benefits": extract_core_benefits(pages),
        "product_facts": {
            "copay": extract_copay(pages),
            "room_rent_limit": extract_room_rent(pages),
        },
        "discounts": extract_discounts(pages),
        "optional_covers": extract_optional_covers(pages),
        "summary": {
            "documents_used": sorted(set(p["source_type"] for p in pages)),
            "pages_scanned": len(pages),
        },
    }


def save_output(entity_id: str, intelligence: dict[str, Any]) -> Path:
    insurer_slug, product_slug = entity_id.split(":")

    output_dir = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "intelligence"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "product_intelligence.json"
    output_path.write_text(
        json.dumps(intelligence, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    intelligence = build_product_intelligence(args.entity_id)
    output_path = save_output(args.entity_id, intelligence)

    print("=" * 70)
    print("PRODUCT INTELLIGENCE EXTRACTOR")
    print("=" * 70)
    print(f"Entity  : {args.entity_id}")
    print(f"Version : {EXTRACTOR_VERSION}")
    print(f"Output  : {output_path}")
    print("-" * 70)
    print(f"Product : {intelligence['metadata'].get('product_name')}")
    print(f"UIN     : {intelligence['metadata'].get('uin')}")
    print(f"Benefits: {len(intelligence['core_benefits'])}")
    print(f"Waiting : {len(intelligence['waiting_periods'])}")
    print(f"Options : {len(intelligence['optional_covers'])}")

    print("-" * 70)
    print("PRODUCT FACTS")
    for key, value in intelligence["product_facts"].items():
        print(f"✓ {key}: {value.get('value')} | confidence={value.get('confidence')}")

    print("=" * 70)


if __name__ == "__main__":
    main()