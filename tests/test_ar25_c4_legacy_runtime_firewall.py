from pathlib import Path


AUTHORITATIVE_ROOTS = (
    Path("factory_core"),
    Path("insurance_intelligence"),
)

# The bypass inventory is the one authoritative location allowed to name legacy paths
# because its purpose is to classify and prove them unreachable.
ALLOWED_REFERENCE_FILES = {
    Path("insurance_intelligence/bypass_inventory/classifier.py"),
}

LEGACY_RUNTIME_TOKENS = (
    "scripts.recommend_products",
    "scripts.compare_products",
    "scripts.build_recommendation_context",
    "recommend_products.py",
    "compare_products.py",
    "build_recommendation_context.py",
    "knowledge/health/recommendations",
    "knowledge\\health\\recommendations",
    "knowledge/health/comparisons",
    "knowledge\\health\\comparisons",
    "knowledge/health/recommendation_contexts",
    "knowledge\\health\\recommendation_contexts",
)


def _authoritative_python_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for root in AUTHORITATIVE_ROOTS:
        files.extend(path for path in root.rglob("*.py") if path.is_file())
    return tuple(sorted(files, key=lambda item: item.as_posix()))


def test_authoritative_runtime_does_not_reference_legacy_recommendation_utilities() -> None:
    violations: list[str] = []
    for path in _authoritative_python_files():
        if path in ALLOWED_REFERENCE_FILES:
            continue
        text = path.read_text(encoding="utf-8").lower()
        matched = tuple(token for token in LEGACY_RUNTIME_TOKENS if token.lower() in text)
        if matched:
            violations.append(f"{path.as_posix()}: {matched}")

    assert violations == []


def test_legacy_utilities_remain_outside_authoritative_packages() -> None:
    legacy_paths = (
        Path("scripts/recommend_products.py"),
        Path("scripts/compare_products.py"),
        Path("scripts/build_recommendation_context.py"),
    )
    assert all(path.exists() for path in legacy_paths)
    assert all(
        not any(path.is_relative_to(root) for root in AUTHORITATIVE_ROOTS)
        for path in legacy_paths
    )


def test_bypass_inventory_is_the_only_authoritative_exception() -> None:
    assert ALLOWED_REFERENCE_FILES == {
        Path("insurance_intelligence/bypass_inventory/classifier.py")
    }
    assert all(path.exists() for path in ALLOWED_REFERENCE_FILES)
