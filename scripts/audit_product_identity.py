from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


IDENTITY_AUDIT_VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_valid_uin(uin: Any) -> bool:
    if not uin or not isinstance(uin, str):
        return False

    value = uin.strip().upper()

    if "XXXXX" in value:
        return False

    return bool(re.match(r"^[A-Z0-9]{10,30}$", value))


def audit_identity(entity_id: str) -> dict[str, Any]:
    insurer_slug, product_slug = entity_id.split(":")

    input_path = (
        BASE_DIR
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "intelligence"
        / "product_intelligence.json"
    )

    if not input_path.exists():
        raise FileNotFoundError(f"Missing product intelligence file: {input_path}")

    intelligence = load_json(input_path)
    metadata = intelligence.get("metadata", {})

    product_name = metadata.get("product_name")
    uin = metadata.get("uin")

    issues = []

    if not intelligence.get("entity_id"):
        issues.append({
            "severity": "ERROR",
            "field": "entity_id",
            "message": "Missing entity_id",
        })

    if intelligence.get("entity_id") != entity_id:
        issues.append({
            "severity": "WARN",
            "field": "entity_id",
            "message": "Entity ID mismatch between input and product intelligence file",
            "value": intelligence.get("entity_id"),
        })

    if not product_name:
        issues.append({
            "severity": "ERROR",
            "field": "metadata.product_name",
            "message": "Missing product name",
        })

    if not is_valid_uin(uin):
        issues.append({
            "severity": "ERROR",
            "field": "metadata.uin",
            "message": "Missing, invalid, or placeholder UIN",
            "value": uin,
        })

    score = 100
    score -= sum(1 for issue in issues if issue["severity"] == "ERROR") * 30
    score -= sum(1 for issue in issues if issue["severity"] == "WARN") * 10
    score = max(score, 0)

    if any(issue["severity"] == "ERROR" for issue in issues):
        status = "FAIL"
    elif issues:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    identity = {
        "entity_id": entity_id,
        "insurer_slug": insurer_slug,
        "product_slug": product_slug,
        "product_name": product_name,
        "uin": uin,
        "identity_key": uin if is_valid_uin(uin) else entity_id,
        "identity_key_type": "uin" if is_valid_uin(uin) else "entity_id",
        "ready_for_deduplication": is_valid_uin(uin),
        "ready_for_policy_ai_matching": is_valid_uin(uin),
        "ready_for_irdai_reconciliation": is_valid_uin(uin),
    }

    report = {
        "entity_id": entity_id,
        "identity_audit_version": IDENTITY_AUDIT_VERSION,
        "input_file": str(input_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "status": status,
        "score": score,
        "error_count": sum(1 for issue in issues if issue["severity"] == "ERROR"),
        "warning_count": sum(1 for issue in issues if issue["severity"] == "WARN"),
        "issues": issues,
        "identity": identity,
    }

    out_dir = BASE_DIR / "knowledge" / "health" / insurer_slug / product_slug / "identity"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "product_identity_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    report["output_file"] = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")

    return report


def print_report(report: dict[str, Any]):
    identity = report["identity"]

    print("=" * 70)
    print("PRODUCT IDENTITY AUDIT")
    print("=" * 70)
    print(f"Entity              : {report['entity_id']}")
    print(f"Version             : {report['identity_audit_version']}")
    print(f"Status              : {report['status']}")
    print(f"Score               : {report['score']}")
    print(f"Product Name        : {identity.get('product_name')}")
    print(f"UIN                 : {identity.get('uin')}")
    print(f"Identity Key        : {identity.get('identity_key')}")
    print(f"Identity Key Type   : {identity.get('identity_key_type')}")
    print(f"Policy-AI Ready     : {identity.get('ready_for_policy_ai_matching')}")
    print(f"IRDAI Ready         : {identity.get('ready_for_irdai_reconciliation')}")
    print(f"Output              : {report['output_file']}")
    print("-" * 70)

    if report["issues"]:
        for issue in report["issues"]:
            print(f"[{issue['severity']}] {issue['field']}")
            print(f"  {issue['message']}")
            if issue.get("value") is not None:
                print(f"  value: {issue['value']}")
    else:
        print("No identity issues found.")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity-id", required=True)
    args = parser.parse_args()

    report = audit_identity(args.entity_id)
    print_report(report)


if __name__ == "__main__":
    main()