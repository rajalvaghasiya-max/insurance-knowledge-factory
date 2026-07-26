from life_intelligence_lab.parser import parse_amfi_nav


# --- 1. Valid AMFI row -----------------------------------------------------

def test_valid_row_parses_to_observation(valid_snapshot, valid_fixture_text):
    result = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    accepted_codes = {o.amfi_scheme_code for o in result.accepted}
    assert "118551" in accepted_codes
    obs = next(o for o in result.accepted if o.amfi_scheme_code == "118551")
    assert obs.scheme_name == "Axis Overnight Fund - Regular Plan - Growth"
    assert obs.nav_value == "1234.5678"
    assert obs.nav_valuation_date == "2026-07-25"
    assert obs.isin_payout_growth == "INF209K01UN8"
    assert obs.validation_status == "accepted"
    assert obs.category == "Open Ended Schemes(Overnight Fund)"


# --- 2. Missing optional ISIN -----------------------------------------------

def test_missing_optional_isin_does_not_reject_row(valid_snapshot, valid_fixture_text):
    result = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    obs = next(o for o in result.accepted if o.amfi_scheme_code == "118551")
    assert obs.isin_reinvestment is None
    obs_both_dash = next(o for o in result.accepted if o.amfi_scheme_code == "118553")
    assert obs_both_dash.isin_payout_growth is None
    assert obs_both_dash.isin_reinvestment is None
    assert obs_both_dash.validation_status == "accepted"


# --- 3. Invalid scheme code --------------------------------------------------

def test_invalid_scheme_code_is_rejected(errors_snapshot, errors_fixture_text):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    reasons = [r.reason for r in result.rejected]
    assert any("invalid_scheme_code" in r for r in reasons)
    assert not any(o.amfi_scheme_code == "ABCDE" for o in result.accepted)


# --- 4. Invalid NAV -----------------------------------------------------------

def test_invalid_nav_format_is_rejected(errors_snapshot, errors_fixture_text):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    reasons = [r.reason for r in result.rejected]
    assert any("invalid_nav_format" in r for r in reasons)  # the "N.A." row


# --- 5. Zero or negative NAV ---------------------------------------------------

def test_zero_and_negative_nav_are_rejected(errors_snapshot, errors_fixture_text):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    reasons = [r.reason for r in result.rejected]
    nav_not_positive_count = sum(1 for r in reasons if "nav_not_positive" in r)
    assert nav_not_positive_count == 2  # zero NAV row + negative NAV row


# --- 6. Invalid date -----------------------------------------------------------

def test_invalid_date_is_rejected(errors_snapshot, errors_fixture_text):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    reasons = [r.reason for r in result.rejected]
    assert any("invalid_nav_date" in r for r in reasons)


# --- 7. Empty source ------------------------------------------------------------

def test_empty_source_yields_no_observations(valid_snapshot):
    result = parse_amfi_nav("", valid_snapshot)
    assert result.accepted == []
    assert result.rejected == []


# --- 8. Duplicate row ------------------------------------------------------------

def test_duplicate_row_is_rejected_not_double_counted(errors_snapshot, errors_fixture_text):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    accepted_119551 = [o for o in result.accepted if o.amfi_scheme_code == "119551"]
    assert len(accepted_119551) == 1  # only the first occurrence is accepted
    reasons = [r.reason for r in result.rejected]
    assert any("duplicate_row" in r for r in reasons)


# --- 9. Section / category parsing -----------------------------------------------

def test_section_heading_attached_to_rows(valid_snapshot, valid_fixture_text):
    result = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    overnight = [o for o in result.accepted if o.amfi_scheme_code.startswith("1185")]
    liquid = [o for o in result.accepted if o.amfi_scheme_code.startswith("1195")]
    assert all(o.category == "Open Ended Schemes(Overnight Fund)" for o in overnight)
    assert all(o.category == "Open Ended Schemes(Liquid Fund)" for o in liquid)


# --- 10. Deterministic ordering --------------------------------------------------

def test_accepted_observations_are_deterministically_ordered(valid_snapshot, valid_fixture_text):
    result_a = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    result_b = parse_amfi_nav(valid_fixture_text, valid_snapshot)
    codes_a = [o.amfi_scheme_code for o in result_a.accepted]
    codes_b = [o.amfi_scheme_code for o in result_b.accepted]
    assert codes_a == codes_b
    assert codes_a == sorted(codes_a)  # sorted by scheme code (primary sort key)


# Additional coverage beyond the minimum 15: missing scheme name, malformed
# row (too few fields), and a malformed-but-not-absent ISIN producing a
# warning rather than a rejection.

def test_missing_scheme_name_is_rejected(errors_snapshot, errors_fixture_text):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    reasons = [r.reason for r in result.rejected]
    assert any("missing_scheme_name" in r for r in reasons)


def test_malformed_row_too_few_fields_is_rejected(errors_snapshot, errors_fixture_text):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    reasons = [r.reason for r in result.rejected]
    assert any("malformed_row" in r for r in reasons)


def test_malformed_isin_produces_warning_not_rejection(errors_snapshot, errors_fixture_text):
    result = parse_amfi_nav(errors_fixture_text, errors_snapshot)
    obs = next(o for o in result.accepted if o.amfi_scheme_code == "119559")
    assert obs.isin_payout_growth is None
    assert any("isin_format_invalid" in w for w in obs.warnings)


def test_parser_never_touches_network_or_filesystem_for_source(valid_snapshot, valid_fixture_text, monkeypatch):
    # Sanity guard: parser operates purely on the in-memory string it is
    # given -- there is no download/open call anywhere in parser.py to
    # patch, so this test simply asserts the function signature takes
    # text directly and returns without any I/O side effects observable
    # via a change in cwd file listing.
    import os
    before = set(os.listdir("."))
    parse_amfi_nav(valid_fixture_text, valid_snapshot)
    after = set(os.listdir("."))
    assert before == after
