from __future__ import annotations

import argparse
import json
from pathlib import Path
from config.settings import BASE_DIR


SOURCE_TYPES = {
    "policy_wording": ["policy_wording", "policy-wording", "policy wording", "wording"],
    "customer_information_sheet": ["customer_information_sheet", "customer-information-sheet", "customer information sheet", "cis"],
    "prospectus": ["prospectus"],
    "brochure": ["brochure"],
    "webpage": ["webpage", "metadata", "html_sections", "html-sections"],
}

PRODUCT_ALIASES = {
    "aditya_birla_health:activ_one": [
        "activ-one", "activ_one", "activ one", "activone",
        "active-one", "active_one", "active one", "activeone",
    ]
}

RELATED_ALIASES = {
    "aditya_birla_health:activ_one": [
        "activonemax", "activ-one-max", "activ one max",
        "activonemaxplus", "activ-one-max-plus", "activ one max plus",
        "activonevytl", "activ-one-vytl", "activ one vytl",
    ]
}

BLOCKED_DIRS = [
    ".venv",
    "__pycache__",
    "routing_plans",
    "routing-plans",
    "extracted_facts",
    "extracted-facts",
]


def read_text(path: Path, limit: int = 12000) -> str:
    if path.suffix.lower() == ".pdf":
        return ""

    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception:
        return ""

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
            return json.dumps(data, ensure_ascii=False).lower()
        except Exception:
            pass

    return raw.lower()


def classify_source(path: Path, text: str) -> str:
    combined = f"{path} {text}".lower().replace("\\", "/").replace("_", "-")

    for source_type, hints in SOURCE_TYPES.items():
        for hint in hints:
            if hint.replace("_", "-") in combined:
                return source_type

    if path.suffix.lower() == ".pdf":
        return "webpage"

    return "webpage"


def matches_entity(path: Path, text: str, entity_id: str) -> bool:
    combined = f"{path} {text}".lower().replace("\\", "/").replace("_", "-")

    for alias in RELATED_ALIASES.get(entity_id, []):
        if alias.replace("_", "-") in combined:
            return False

    for alias in PRODUCT_ALIASES.get(entity_id, []):
        if alias.replace("_", "-") in combined:
            return True

    return False


def audit(entity_id: str):
    evidence = {source_type: [] for source_type in SOURCE_TYPES}

    for root_name in ["knowledge", "parsed", "archive"]:
        root = BASE_DIR / root_name

        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            lower_path = str(path).lower().replace("\\", "/")

            if any(blocked in lower_path for blocked in BLOCKED_DIRS):
                continue

            if path.suffix.lower() not in [".json", ".txt", ".md", ".pdf"]:
                continue

            text = read_text(path)

            if not matches_entity(path, text, entity_id):
                continue

            source_type = classify_source(path, text)
            evidence[source_type].append(str(path.relative_to(BASE_DIR)).replace("\\", "/"))

    coverage = {k: bool(v) for k, v in evidence.items()}
    score = round(sum(coverage.values()) / len(coverage) * 100)

    report = {
        "entity_id": entity_id,
        "coverage_score": score,
        "status": "READY" if score >= 80 else "PARTIAL" if score >= 40 else "INCOMPLETE",
        "coverage": coverage,
        "evidence": evidence,
    }

    out_dir = BASE_DIR / "knowledge" / "health" / "coverage_audits"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{entity_id.replace(':', '_')}_coverage_audit.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 70)
    print("EVIDENCE COVERAGE AUDIT")
    print("=" * 70)
    print(f"Entity         : {entity_id}")
    print(f"Coverage Score : {score}%")
    print(f"Status         : {report['status']}")
    print(f"Output         : {out_path}")
    print("-" * 70)

    for source_type, exists in coverage.items():
        symbol = "✓" if exists else "✗"
        print(f"{symbol} {source_type:<30} {len(evidence[source_type])}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    audit(args.entity_id)


if __name__ == "__main__":
    main()