import json
from pathlib import Path

import pytest

from scripts import audit_product_identity


ENTITY_ID = "test_insurer:test_product"


def write_product_intelligence(
    base_dir: Path,
    entity_id: str = ENTITY_ID,
    product_name: str = "Test Health Plan",
    uin: str = "ABC1234567V01",
    intelligence_entity_id: str | None = None,
) -> Path:
    insurer_slug, product_slug = entity_id.split(":")
    input_dir = (
        base_dir
        / "knowledge"
        / "health"
        / insurer_slug
        / product_slug
        / "intelligence"
    )
    input_dir.mkdir(parents=True)
    input_path = input_dir / "product_intelligence.json"
    input_path.write_text(
        json.dumps(
            {
                "entity_id": intelligence_entity_id or entity_id,
                "metadata": {
                    "product_name": product_name,
                    "uin": uin,
                },
            }
        ),
        encoding="utf-8",
    )
    return input_path


@pytest.fixture
def isolated_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_product_identity, "BASE_DIR", tmp_path)
    return tmp_path


def test_audit_identity_passes_with_valid_uin(isolated_base_dir):
    write_product_intelligence(isolated_base_dir, uin="ABC1234567V01")

    report = audit_product_identity.audit_identity(ENTITY_ID)

    assert report["status"] == "PASS"
    assert report["score"] == 100
    assert report["error_count"] == 0
    assert report["warning_count"] == 0
    assert report["issues"] == []
    assert report["identity"]["identity_key"] == "ABC1234567V01"
    assert report["identity"]["identity_key_type"] == "uin"
    assert report["identity"]["ready_for_deduplication"] is True
    assert report["identity"]["ready_for_policy_ai_matching"] is True
    assert report["identity"]["ready_for_irdai_reconciliation"] is True
    assert report["output_file"] == (
        "knowledge/health/test_insurer/test_product/identity/"
        "product_identity_report.json"
    )

    output_path = isolated_base_dir / report["output_file"]
    assert json.loads(output_path.read_text(encoding="utf-8"))["status"] == "PASS"


def test_audit_identity_fails_with_placeholder_uin(isolated_base_dir):
    write_product_intelligence(isolated_base_dir, uin="XXXXX12345")

    report = audit_product_identity.audit_identity(ENTITY_ID)

    assert report["status"] == "FAIL"
    assert report["score"] == 70
    assert report["error_count"] == 1
    assert report["warning_count"] == 0
    assert report["identity"]["identity_key"] == ENTITY_ID
    assert report["identity"]["identity_key_type"] == "entity_id"
    assert report["identity"]["ready_for_deduplication"] is False
    assert report["issues"] == [
        {
            "severity": "ERROR",
            "field": "metadata.uin",
            "message": "Missing, invalid, or placeholder UIN",
            "value": "XXXXX12345",
        }
    ]


def test_audit_identity_raises_when_product_intelligence_missing(isolated_base_dir):
    with pytest.raises(FileNotFoundError, match="Missing product intelligence file"):
        audit_product_identity.audit_identity(ENTITY_ID)


def test_audit_identity_warns_on_entity_id_mismatch(isolated_base_dir):
    write_product_intelligence(
        isolated_base_dir,
        entity_id=ENTITY_ID,
        intelligence_entity_id="different_insurer:different_product",
        uin="ABC1234567V01",
    )

    report = audit_product_identity.audit_identity(ENTITY_ID)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["score"] == 90
    assert report["error_count"] == 0
    assert report["warning_count"] == 1
    assert report["issues"] == [
        {
            "severity": "WARN",
            "field": "entity_id",
            "message": "Entity ID mismatch between input and product intelligence file",
            "value": "different_insurer:different_product",
        }
    ]
