from capability_control.catalog import CapabilityCatalog, CapabilityRecord
from capability_control.development_protocol import (
    CapabilityImpactDeclaration,
    ChangedPath,
    evaluate_development_protocol,
)
from capability_control.scanner import CapabilityDriftReport


def _record(
    capability_id="PLATFORM.A",
    *,
    ownership_paths=("capability_control/a.py",),
    lifecycle_status="ACTIVE",
    supersedes=(),
    superseded_by=None,
):
    return CapabilityRecord(
        capability_id=capability_id,
        name=capability_id,
        responsibility="Govern a deterministic responsibility",
        plane="PLATFORM",
        lifecycle_status=lifecycle_status,
        authority_role="bounded authority",
        safety_invariants=("fail closed",),
        reuse_policy="REUSE",
        ownership_paths=ownership_paths,
        introduced_by="TEST",
        supersedes=supersedes,
        superseded_by=superseded_by,
        notes=None,
    )


def _catalog(*records):
    return CapabilityCatalog(
        catalog_version="1.0",
        enforcement_mode="RECONCILIATION",
        governed_roots=("capability_control", "insurance_intelligence"),
        capabilities=tuple(records),
    )


def _scanner(*, unclaimed=()):
    return CapabilityDriftReport(
        missing_governed_roots=(),
        missing_ownership_paths=(),
        unclaimed_governed_files=tuple(unclaimed),
        stale_ownership_paths=(),
        strict_failure_reasons=(),
    )


def _fp(*items):
    return {
        "capabilities": [
            {
                "capability_id": capability_id,
                "owned_module_paths": list(paths),
                "structural_fingerprint": fingerprint,
            }
            for capability_id, paths, fingerprint in items
        ]
    }


def _decl(classification="EXTEND", ids=("PLATFORM.A",), rationale=""):
    return CapabilityImpactDeclaration(
        change_id="change",
        classification=classification,
        capability_ids=ids,
        rationale=rationale,
        supersession_impact="NONE",
        authority_impact="Governance-only change",
    )


def _evaluate(
    *,
    changes,
    declaration,
    base_catalog=None,
    current_catalog=None,
    base_fp=None,
    current_fp=None,
    unclaimed=(),
):
    base_catalog = base_catalog or _catalog(_record())
    current_catalog = current_catalog or base_catalog
    base_fp = base_fp or _fp(("PLATFORM.A", ("capability_control/a.py",), "a" * 64))
    current_fp = current_fp or base_fp
    return evaluate_development_protocol(
        changes=tuple(changes),
        base_catalog=base_catalog,
        current_catalog=current_catalog,
        scanner_report=_scanner(unclaimed=unclaimed),
        base_fingerprints=base_fp,
        current_fingerprints=current_fp,
        declaration=declaration,
    )


def test_governed_change_requires_committed_declaration():
    report = _evaluate(
        changes=(ChangedPath("M", "capability_control/a.py"),),
        declaration=None,
    )
    assert "CAPABILITY_IMPACT_DECLARATION_REQUIRED" in report.errors
    assert "EXACTLY_ONE_NEW_CAPABILITY_IMPACT_RECORD_REQUIRED" in report.errors


def test_fingerprint_change_must_name_actual_capability():
    base = _fp(
        ("PLATFORM.A", ("capability_control/a.py",), "a" * 64),
        ("PLATFORM.B", ("capability_control/b.py",), "b" * 64),
    )
    head = _fp(
        ("PLATFORM.A", ("capability_control/a.py",), "a" * 64),
        ("PLATFORM.B", ("capability_control/b.py",), "c" * 64),
    )
    catalog = _catalog(_record(), _record("PLATFORM.B", ownership_paths=("capability_control/b.py",)))
    report = _evaluate(
        changes=(
            ChangedPath("M", "capability_control/b.py"),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=_decl(ids=("PLATFORM.A",)),
        base_catalog=catalog,
        current_catalog=catalog,
        base_fp=base,
        current_fp=head,
    )
    assert "UNDECLARED_CAPABILITY_CHANGE PLATFORM.B" in report.errors


def test_reuse_cannot_add_governed_implementation():
    report = _evaluate(
        changes=(
            ChangedPath("A", "capability_control/new_helper.py"),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=_decl(classification="REUSE"),
    )
    assert "REUSE_CANNOT_ADD_GOVERNED_IMPLEMENTATION" in report.errors


def test_unclaimed_governed_addition_fails_closed_without_new_review():
    path = "insurance_intelligence/new_authority.py"
    report = _evaluate(
        changes=(
            ChangedPath("A", path),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=_decl(classification="EXTEND"),
        unclaimed=(path,),
    )
    assert f"UNCLAIMED_GOVERNED_CODE_REQUIRES_NEW_REVIEW {path}" in report.errors


def test_new_declaration_does_not_authorize_unregistered_code():
    path = "insurance_intelligence/new_authority.py"
    report = _evaluate(
        changes=(
            ChangedPath("A", path),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=_decl(classification="NEW", rationale="No reusable capability exists."),
        unclaimed=(path,),
    )
    assert f"NEW_CAPABILITY_REQUIRES_CATALOG_REGISTRATION {path}" in report.errors


def test_new_requires_new_catalog_capability_and_added_implementation():
    report = _evaluate(
        changes=(
            ChangedPath("M", "capability_control/a.py"),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=_decl(classification="NEW", rationale="No reusable capability exists."),
    )
    assert "NEW_REQUIRES_NEW_CATALOG_CAPABILITY" in report.errors
    assert "NEW_REQUIRES_ADDED_GOVERNED_IMPLEMENTATION" in report.errors


def test_valid_new_is_declared_registered_and_claimed():
    base_catalog = _catalog(_record())
    new_record = _record(
        "PLATFORM.NEW",
        ownership_paths=("capability_control/new_authority.py",),
    )
    current_catalog = _catalog(_record(), new_record)
    base_fp = _fp(("PLATFORM.A", ("capability_control/a.py",), "a" * 64))
    head_fp = _fp(
        ("PLATFORM.A", ("capability_control/a.py",), "a" * 64),
        ("PLATFORM.NEW", ("capability_control/new_authority.py",), "n" * 64),
    )
    declaration = CapabilityImpactDeclaration(
        change_id="change",
        classification="NEW",
        capability_ids=("PLATFORM.NEW",),
        rationale="Repository preflight found no reusable or extensible authority.",
        supersession_impact="NONE",
        authority_impact="Introduces a bounded new platform authority.",
    )
    report = _evaluate(
        changes=(
            ChangedPath("A", "capability_control/new_authority.py"),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
            ChangedPath("A", "governance/capabilities/catalog.d/new.json"),
            ChangedPath("M", "governance/capabilities/generated/structural_fingerprints.json"),
        ),
        declaration=declaration,
        base_catalog=base_catalog,
        current_catalog=current_catalog,
        base_fp=base_fp,
        current_fp=head_fp,
    )
    assert report.errors == ()


def test_replace_requires_catalog_lineage_change():
    declaration = CapabilityImpactDeclaration(
        change_id="change",
        classification="REPLACE",
        capability_ids=("PLATFORM.A",),
        rationale="Replacement is required.",
        supersession_impact="PLATFORM.A will be superseded.",
        authority_impact="Authority transfers explicitly.",
    )
    report = _evaluate(
        changes=(
            ChangedPath("M", "capability_control/a.py"),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=declaration,
    )
    assert "REPLACE_REQUIRES_CATALOG_LINEAGE_CHANGE" in report.errors


def test_replace_passes_when_bidirectional_lineage_changes():
    old_base = _record("PLATFORM.OLD", ownership_paths=("capability_control/old.py",))
    new_base = _record("PLATFORM.NEW", ownership_paths=("capability_control/new.py",))
    base_catalog = _catalog(old_base, new_base)
    old_head = _record(
        "PLATFORM.OLD",
        ownership_paths=("capability_control/old.py",),
        lifecycle_status="SUPERSEDED",
        superseded_by="PLATFORM.NEW",
    )
    new_head = _record(
        "PLATFORM.NEW",
        ownership_paths=("capability_control/new.py",),
        supersedes=("PLATFORM.OLD",),
    )
    current_catalog = _catalog(old_head, new_head)
    fp = _fp(
        ("PLATFORM.OLD", ("capability_control/old.py",), "o" * 64),
        ("PLATFORM.NEW", ("capability_control/new.py",), "n" * 64),
    )
    declaration = CapabilityImpactDeclaration(
        change_id="change",
        classification="REPLACE",
        capability_ids=("PLATFORM.OLD", "PLATFORM.NEW"),
        rationale="Explicit authority replacement.",
        supersession_impact="OLD is superseded by NEW.",
        authority_impact="Authority moves only through catalog lineage.",
    )
    report = _evaluate(
        changes=(
            ChangedPath("M", "governance/capabilities/catalog.d/replace.json"),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=declaration,
        base_catalog=base_catalog,
        current_catalog=current_catalog,
        base_fp=fp,
        current_fp=fp,
    )
    assert report.errors == ()


def test_existing_impact_records_are_immutable():
    report = _evaluate(
        changes=(
            ChangedPath("M", "capability_control/a.py"),
            ChangedPath("M", "governance/capabilities/impacts/old-change.json"),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=_decl(),
    )
    assert "CAPABILITY_IMPACT_RECORD_IMMUTABLE" in report.errors


def test_capability_removal_fails_even_when_declared():
    base_fp = _fp(("PLATFORM.A", ("capability_control/a.py",), "a" * 64))
    head_fp = _fp()
    report = _evaluate(
        changes=(
            ChangedPath("D", "capability_control/a.py"),
            ChangedPath("A", "governance/capabilities/impacts/change.json"),
        ),
        declaration=_decl(classification="REPLACE", rationale="Replace explicitly."),
        base_fp=base_fp,
        current_fp=head_fp,
    )
    assert "CAPABILITY_REMOVAL_REQUIRES_RETAINED_LINEAGE PLATFORM.A" in report.errors


def test_non_governed_document_change_needs_no_declaration():
    report = _evaluate(
        changes=(ChangedPath("M", "README.md"),),
        declaration=None,
    )
    assert report.declaration_required is False
    assert report.errors == ()
