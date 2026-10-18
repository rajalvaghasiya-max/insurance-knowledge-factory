from __future__ import annotations

from scripts.run_health_customer_v0_dev_seed import EXPECTED_ROUTE, load_dev_seed_cases


def test_dev_seed_runner_loads_exact_preregistered_six_cases() -> None:
    cases = load_dev_seed_cases()

    assert len(cases) == 6
    assert {item["concept_area"] for item in cases} == set(EXPECTED_ROUTE)
    assert len({item["case_id"] for item in cases}) == 6
    assert all(item["user_text"].strip() for item in cases)


def test_dev_seed_expected_routes_are_unique() -> None:
    routes = tuple(EXPECTED_ROUTE.values())

    assert len(routes) == len(set(routes))
