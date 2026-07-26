from datetime import date
from decimal import Decimal

from life_intelligence_lab.calculators.adapters.pyxirr_adapter import (
    DependencyFailureError,
    INSTALLED_DEPENDENCY_VERSION,
    PINNED_DEPENDENCY_VERSION,
    PyXirrAdapter,
    count_sign_changes,
    dependency_fingerprint,
    supported_day_count_conventions,
)


def test_installed_version_matches_pinned_version():
    assert INSTALLED_DEPENDENCY_VERSION == PINNED_DEPENDENCY_VERSION


def test_dependency_fingerprint_contains_version_and_adapter_id():
    fp = dependency_fingerprint()
    assert "pyxirr" in fp
    assert PINNED_DEPENDENCY_VERSION in fp
    assert "PyXirrAdapter" in fp


def test_act_365_is_supported():
    assert "ACT_365" in supported_day_count_conventions()


def test_unsupported_day_count_raises():
    adapter = PyXirrAdapter()
    try:
        adapter.xirr([(date(2020, 1, 1), Decimal("-1")), (date(2021, 1, 1), Decimal("2"))], "THIRTY_360")
        assert False
    except ValueError as exc:
        assert "unsupported_day_count_convention" in str(exc)


def test_xirr_known_answer_via_adapter():
    adapter = PyXirrAdapter()
    dated = [
        (date(2020, 1, 1), Decimal("-10000")),
        (date(2020, 3, 1), Decimal("5750")),
        (date(2020, 10, 30), Decimal("4250")),
        (date(2021, 2, 15), Decimal("3250")),
    ]
    outcome = adapter.xirr(dated, "ACT_365")
    assert outcome.converged is True
    assert str(outcome.value).startswith("0.634297261526")


def test_all_positive_maps_to_not_converged_not_exception():
    adapter = PyXirrAdapter()
    outcome = adapter.xirr([(date(2020, 1, 1), Decimal("100")), (date(2020, 6, 1), Decimal("200"))], "ACT_365")
    assert outcome.converged is False
    assert outcome.raw_exception_type == "InvalidPaymentsError"


def test_xnpv_rate_le_negative_one_returns_domain_failure_not_exception():
    adapter = PyXirrAdapter()
    dated = [(date(2020, 1, 1), Decimal("-100")), (date(2021, 1, 1), Decimal("200"))]
    outcome = adapter.xnpv(Decimal("-1"), dated, "ACT_365")
    assert outcome.converged is False
    assert "rate_out_of_domain" in outcome.error_reason


def test_sign_changes_single():
    assert count_sign_changes([Decimal("-1"), Decimal("1"), Decimal("1")]) == 1


def test_sign_changes_multiple():
    assert count_sign_changes([Decimal("-1"), Decimal("1"), Decimal("-1")]) == 2


def test_sign_changes_ignores_zero():
    assert count_sign_changes([Decimal("-1"), Decimal("0"), Decimal("1")]) == 1


class _CrashingEngine:
    class InvalidPaymentsError(Exception):
        pass

    def xirr(self, *args, **kwargs):
        raise RuntimeError("simulated catastrophic engine failure")

    def xnpv(self, *args, **kwargs):
        raise RuntimeError("simulated catastrophic engine failure")


def test_dependency_failure_is_raised_not_swallowed():
    adapter = PyXirrAdapter(engine=_CrashingEngine())
    dated = [(date(2020, 1, 1), Decimal("-100")), (date(2021, 1, 1), Decimal("200"))]
    try:
        adapter.xirr(dated, "ACT_365")
        assert False
    except DependencyFailureError as exc:
        assert "RuntimeError" in str(exc)


def test_dependency_failure_is_distinct_from_invalid_payments():
    adapter = PyXirrAdapter()
    outcome = adapter.xirr([(date(2020, 1, 1), Decimal("100")), (date(2020, 6, 1), Decimal("200"))], "ACT_365")
    assert outcome.converged is False  # not an exception at all
