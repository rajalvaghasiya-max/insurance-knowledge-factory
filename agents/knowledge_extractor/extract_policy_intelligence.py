from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


EXTRACTOR_VERSION = "0.4"

PRODUCT_FACT_DEFINITIONS = {
    "copay": ["co-payment", "co payment", "copay", "co-pay"],
    "room_rent_limit": ["room rent", "room rent type", "single private room", "shared accommodation"],
    "restoration_benefit": ["super reload", "reload", "restoration", "restore"],
    "ayush_cover": ["ayush treatment", "ayush"],
    "day_care_treatment": ["day care treatment", "all day care"],
    "domiciliary_treatment": ["domiciliary hospitalization", "domiciliary"],
    "maternity_cover": ["maternity cover", "maternity expenses", "maternity"],
}

SOURCE_PRIORITY = {
    "waiting_periods": ["customer_information_sheet", "policy_wording", "prospectus"],
    "exclusions": ["policy_wording", "customer_information_sheet", "prospectus"],
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    text = text.replace("\u001f", " ")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def source_rank(source_type: str, group: str) -> int:
    try:
        return SOURCE_PRIORITY[group].index(source_type)
    except ValueError:
        return 99


def source_ref(doc: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": doc.get("source_type"),
        "source_file": doc.get("source_file"),
        "page_number": page.get("page_number"),
    }


def extract_metadata(all_pages: list[dict[str, Any]]) -> dict[str, Any]:
    joined = "\n".join(p["text"] for p in all_pages[:10])

    product_name = None
    uin = None

    m = re.search(r"Product Name\s*:\s*([^,\n]+)", joined, re.I)
    if m:
        product_name = m.group(1).strip()

    m = re.search(r"Product UIN\s*:\s*([A-Z0-9]+)", joined, re.I)
    if m:
        uin = m.group(1).strip()

    return {"product_name": product_name, "uin": uin}


def split_into_clauses(text: str) -> list[dict[str, str]]:
    """
    Clause splitter v0.3.
    Splits page text around legal section markers:
      D.1.1, D.1.2, D.1.3, etc.
    """

    text = normalize(text)

    matches = list(re.finditer(r"\b(D\.\d+(?:\.\d+)?)\.?\s+", text))

    if not matches:
        return [{"code": None, "text": text}]

    clauses = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        code = match.group(1)
        clause_text = text[start:end].strip()

        if len(clause_text) > 30:
            clauses.append({"code": code, "text": clause_text})

    return clauses


def duration_months(text: str, target: str | None = None) -> int | None:
    lower = text.lower()

    # Target-aware extraction for mixed CIS snippets.
    # Example:
    # PED = 36 months
    # Specified disease = 24 months
    # on same page/snippet.
    if target == "specified_disease_waiting_period":
        specified_patterns = [
            r"specified disease[^.:\n]*?(?:waiting period)?[^.:\n]*?(24 months|2 years)",
            r"specific disease[^.:\n]*?(?:waiting period)?[^.:\n]*?(24 months|2 years)",
            r"24 months[^.:\n]*?specific illness",
            r"24 months[^.:\n]*?specified",
        ]

        for pattern in specified_patterns:
            if re.search(pattern, lower, flags=re.IGNORECASE):
                return 24

    if target == "pre_existing_disease_waiting_period":
        ped_patterns = [
            r"pre-existing disease[^.:\n]*?(36 months|3 years)",
            r"pre existing disease[^.:\n]*?(36 months|3 years)",
            r"ped[^.:\n]*?(36 months|3 years)",
            r"36 months[^.:\n]*?pre-existing",
            r"36 months[^.:\n]*?pre existing",
        ]

        for pattern in ped_patterns:
            if re.search(pattern, lower, flags=re.IGNORECASE):
                return 36

    if "36 months" in lower or "3 years" in lower:
        return 36
    if "24 months" in lower or "2 years" in lower:
        return 24
    if "12 months" in lower or "1 year" in lower:
        return 12

    return None


def extract_title_from_clause(code: str | None, text: str) -> str | None:
    if not code:
        return None

    after_code = text.split(code, 1)[-1].strip()

    after_code = re.sub(r"^\.*\s*", "", after_code)

    title = re.split(
        r"\s+(?:a\)|Expenses|Treatment|Pre-existing|Specified|30-day|Medical|If|The|We shall|This)",
        after_code,
        maxsplit=1,
    )[0]

    title = normalize(title)
    title = title.replace("(Code- Excl", "(Code-Excl")

    if len(title) < 3 or len(title) > 100:
        return None

    if "product name" in title.lower():
        return None

    return title


def clause_source(doc: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    return source_ref(doc, page)


def extract_waiting_periods(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts = []

    for doc in docs:
        for page in doc.get("pages", []):
            text = normalize(page.get("text", ""))
            lower = text.lower()
            source = clause_source(doc, page)

            clauses = split_into_clauses(text)

            for clause in clauses:
                ctext = clause["text"]
                clower = ctext.lower()
                code = clause["code"]

                # PED waiting period
                if (
                    code == "D.1.1"
                    or "pre-existing diseases" in clower
                    or "pre existing diseases" in clower
                    or "pre-existing disease" in clower
                    or "pre existing disease" in clower
                ):
                    months = duration_months(ctext, target="pre_existing_disease_waiting_period")
                    if months:
                        facts.append(
                            {
                                "type": "pre_existing_disease_waiting_period",
                                "duration_months": months,
                                "raw_text": ctext[:1400],
                                "source": source,
                                "confidence": 0.97 if months == 36 else 0.75,
                                "validated": months == 36,
                            }
                        )

                # Specified disease waiting period
                if (
                    code == "D.1.2"
                    or "specified disease / procedure waiting period" in clower
                    or "specified disease waiting period" in clower
                    or "specific disease waiting period" in clower
                ):
                    months = duration_months(ctext, target="specified_disease_waiting_period")
                    if months:
                        facts.append(
                            {
                                "type": "specified_disease_waiting_period",
                                "duration_months": months,
                                "raw_text": ctext[:1400],
                                "source": source,
                                "confidence": 0.97 if months == 24 else 0.75,
                                "validated": months == 24,
                            }
                        )

            # Initial waiting period may be in non-D clause table area
            if "30-day waiting period" in lower or "30 days for all illnesses" in lower:
                snippet = extract_snippet(text, ["30-day waiting period", "30 days for all illnesses"])
                if "accident" in snippet.lower():
                    facts.append(
                        {
                            "type": "initial_waiting_period",
                            "duration_days": 30,
                            "applies_to": "illness",
                            "exception": "accident",
                            "raw_text": snippet,
                            "source": source,
                            "confidence": 0.98,
                            "validated": True,
                        }
                    )

            if "critical illness" in lower and "60 days" in lower:
                snippet = extract_snippet(text, ["critical illness", "60 days"])
                facts.append(
                    {
                        "type": "critical_illness_initial_waiting_period",
                        "duration_days": 60,
                        "raw_text": snippet,
                        "source": source,
                        "confidence": 0.92,
                        "validated": True,
                    }
                )

    return choose_best_waiting_facts(facts)


def extract_snippet(text: str, terms: list[str], window: int = 1000) -> str:
    lower = text.lower()

    positions = []
    for term in terms:
        pos = lower.find(term.lower())
        if pos >= 0:
            positions.append(pos)

    if not positions:
        return text[:window]

    pos = min(positions)
    start = max(0, pos - 300)
    end = min(len(text), pos + window)

    return normalize(text[start:end])


def choose_best_waiting_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best = {}

    for fact in facts:
        key = fact["type"]
        current = best.get(key)

        if current is None:
            best[key] = fact
            continue

        new_rank = source_rank(fact["source"]["source_type"], "waiting_periods")
        old_rank = source_rank(current["source"]["source_type"], "waiting_periods")

        if new_rank < old_rank:
            best[key] = fact
        elif new_rank == old_rank:
            if fact.get("validated") and not current.get("validated"):
                best[key] = fact
            elif fact.get("confidence", 0) > current.get("confidence", 0):
                best[key] = fact

    return list(best.values())


def extract_exclusions(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exclusions = []

    for doc in docs:
        source_type = doc.get("source_type")

        for page in doc.get("pages", []):
            text = normalize(page.get("text", ""))
            lower = text.lower()

            if "excl" not in lower and "exclusion" not in lower:
                continue

            clauses = split_into_clauses(text)

            for clause in clauses:
                code = clause["code"]
                ctext = clause["text"]

                if not code:
                    continue

                if not code.startswith("D."):
                    continue

                title = extract_title_from_clause(code, ctext)

                if not title:
                    continue

                exclusions.append(
                    {
                        "code": code,
                        "title": title,
                        "description": ctext[:1200],
                        "source": source_ref(doc, page),
                        "confidence": 0.9 if source_type == "policy_wording" else 0.8,
                    }
                )

    return dedupe_exclusions(exclusions)


def dedupe_exclusions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best = {}

    for item in items:
        code = item["code"]
        current = best.get(code)

        if current is None:
            best[code] = item
            continue

        new_rank = source_rank(item["source"]["source_type"], "exclusions")
        old_rank = source_rank(current["source"]["source_type"], "exclusions")

        if new_rank < old_rank:
            best[code] = item
        elif new_rank == old_rank and len(item.get("description", "")) > len(current.get("description", "")):
            best[code] = item

    return [best[k] for k in sorted(best.keys(), key=code_sort_key)]


def code_sort_key(code: str):
    nums = re.findall(r"\d+", code)
    return tuple(int(n) for n in nums)


def load_docs(entity_id: str) -> list[dict[str, Any]]:
    insurer_slug, product_slug = entity_id.split(":")

    parsed_dir = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "parsed"
    )

    docs = []

    for filename in [
        "customer_information_sheet.json",
        "policy_wording.json",
        "prospectus.json",
    ]:
        path = parsed_dir / filename
        if path.exists():
            docs.append(load_json(path))

    if not docs:
        raise FileNotFoundError(f"No parsed documents found in {parsed_dir}")

    return docs

def extract_product_facts(docs):
    facts = {}

    for doc in docs:
        for page in doc.get("pages", []):
            text = normalize(page.get("text", ""))
            lower = text.lower()
            source = source_ref(doc, page)

            for field, keywords in PRODUCT_FACT_DEFINITIONS.items():
                if field in facts:
                    continue

                if not any(k in lower for k in keywords):
                    continue

                snippet = extract_snippet(text, keywords, window=1200)

                value = "Mentioned, review required"
                confidence = 0.65

                if field == "copay":
                    if "nil" in snippet.lower() or "not applicable" in snippet.lower():
                        value = "Nil / Not applicable"
                        confidence = 0.92

                elif field == "room_rent_limit":
                    if "single private room" in snippet.lower():
                        value = "Single Private Room"
                        confidence = 0.94
                    elif "shared accommodation" in snippet.lower():
                        value = "Shared Accommodation option"
                        confidence = 0.88

                elif field == "restoration_benefit":
                    value = "Super Reload / Restoration available"
                    confidence = 0.93

                elif field in [
                    "ayush_cover",
                    "day_care_treatment",
                    "domiciliary_treatment",
                ]:
                    value = True
                    confidence = 0.90

                elif field == "maternity_cover":
                    value = "Conditional / as per policy schedule"
                    confidence = 0.80

                facts[field] = {
                    "field": field,
                    "value": value,
                    "raw_text": snippet,
                    "source": source,
                    "confidence": confidence,
                    "validated": confidence >= 0.9,
                }

    return facts

def build_policy_intelligence(entity_id: str) -> dict[str, Any]:
    docs = load_docs(entity_id)

    all_pages = []

    for doc in docs:
        for page in doc.get("pages", []):
            all_pages.append(
                {
                    "source_type": doc.get("source_type"),
                    "source_file": doc.get("source_file"),
                    "page_number": page.get("page_number"),
                    "text": normalize(page.get("text", "")),
                }
            )

    metadata = extract_metadata(all_pages)
    waiting_periods = extract_waiting_periods(docs)
    exclusions = extract_exclusions(docs)
    product_facts = extract_product_facts(docs)

    return {
        "entity_id": entity_id,
        "extractor_version": EXTRACTOR_VERSION,
        "metadata": metadata,
        "waiting_periods": waiting_periods,
        "exclusions": exclusions,
        "summary": {
            "waiting_periods_count": len(waiting_periods),
            "exclusions_count": len(exclusions),
            "product_facts_count": len(product_facts),
        },
        "product_facts": product_facts,
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

    output_path = output_dir / "policy_intelligence.json"
    output_path.write_text(
        json.dumps(intelligence, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    intelligence = build_policy_intelligence(args.entity_id)
    output_path = save_output(args.entity_id, intelligence)

    print("=" * 70)
    print("POLICY INTELLIGENCE EXTRACTOR")
    print("=" * 70)
    print(f"Entity   : {args.entity_id}")
    print(f"Version  : {EXTRACTOR_VERSION}")
    print(f"Output   : {output_path}")
    print("-" * 70)
    print(f"Product  : {intelligence['metadata'].get('product_name')}")
    print(f"UIN      : {intelligence['metadata'].get('uin')}")
    print(f"Waiting Periods : {len(intelligence['waiting_periods'])}")
    print(f"Exclusions       : {len(intelligence['exclusions'])}")
    print("-" * 70)

    for item in intelligence["waiting_periods"]:
        value = item.get("duration_months") or item.get("duration_days")
        unit = "months" if item.get("duration_months") else "days"
        print(f"✓ {item['type']} = {value} {unit} | validated={item.get('validated')}")

    print("=" * 70)


if __name__ == "__main__":
    main()