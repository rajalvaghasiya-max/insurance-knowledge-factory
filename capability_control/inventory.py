"""Machine-derived repository inventory for the PolicyScna Capability Control Plane.

This module is structural evidence only. It answers what Python code exists and
how modules are statically connected; it never decides capability authority or
lifecycle. Those remain semantic catalog responsibilities.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping

from .catalog import CapabilityCatalog, CapabilityRecord

INVENTORY_SCHEMA_VERSION = "1.0"
DEFAULT_STRUCTURAL_ROOTS = (
    "agents", "collectors", "factory_core", "factory_sdk", "insurance_intelligence",
    "knowledge", "knowledge_domains", "knowledge_factory", "orchestration", "scripts",
)


@dataclass(frozen=True)
class RepositoryModuleRecord:
    module_id: str
    path: str
    package: str
    sha256: str
    git_blob_sha: str
    loc: int
    doc: str | None
    classes: tuple[str, ...]
    public_functions: tuple[str, ...]
    internal_imports: tuple[str, ...]
    external_imports: tuple[str, ...]
    unresolved_imports: tuple[str, ...]
    imported_by: tuple[str, ...]
    is_entrypoint: bool
    entrypoint_reachable: bool
    test_reachable: bool
    uses_dynamic_import: bool
    parse_error: str | None


@dataclass(frozen=True)
class RepositoryInventory:
    schema_version: str
    content_digest: str
    records: tuple[RepositoryModuleRecord, ...]

    @property
    def by_module_id(self) -> dict[str, RepositoryModuleRecord]:
        return {record.module_id: record for record in self.records}

    @property
    def by_path(self) -> dict[str, RepositoryModuleRecord]:
        return {record.path: record for record in self.records}


@dataclass(frozen=True)
class CapabilityStructuralFingerprint:
    capability_id: str
    owned_module_paths: tuple[str, ...]
    structural_fingerprint: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _path_to_module(path: str) -> str:
    stem = path[:-3]
    if stem.endswith("/__init__"):
        stem = stem[: -len("/__init__")]
    return stem.replace("/", ".")


def _first_party_roots(repo_root: Path) -> tuple[str, ...]:
    roots = {name for name in DEFAULT_STRUCTURAL_ROOTS if (repo_root / name).is_dir()}
    roots.update(
        path.name
        for path in repo_root.iterdir()
        if path.is_dir() and (path / "__init__.py").is_file()
    )
    return tuple(sorted(roots))


def _iter_python_files(repo_root: Path, roots: Iterable[str]) -> tuple[str, ...]:
    paths: list[str] = []
    for root in roots:
        absolute = repo_root / root
        if not absolute.is_dir():
            continue
        for path in sorted(absolute.rglob("*.py")):
            if "__pycache__" in path.parts or any(part.startswith(".") for part in path.parts):
                continue
            paths.append(path.relative_to(repo_root).as_posix())
    return tuple(paths)


def _resolve_relative_base(module_id: str, *, is_package: bool, level: int) -> tuple[str, ...]:
    parts = module_id.split(".")
    anchor = parts if is_package else parts[:-1]
    ascend = max(level - 1, 0)
    if ascend:
        anchor = anchor[:-ascend] if ascend <= len(anchor) else []
    return tuple(anchor)


def _classify_import(name: str, all_modules: frozenset[str]) -> tuple[str, str]:
    if name in all_modules or any(module.startswith(name + ".") for module in all_modules):
        return "internal", name
    top = name.split(".")[0]
    if any(module == top or module.startswith(top + ".") for module in all_modules):
        return "internal", name
    return "external", top


def _extract_imports(
    tree: ast.AST,
    *,
    module_id: str,
    is_package: bool,
    all_modules: frozenset[str],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], bool]:
    internal: set[str] = set()
    external: set[str] = set()
    unresolved: set[str] = set()
    dynamic = False

    def add(name: str) -> None:
        kind, value = _classify_import(name, all_modules)
        (internal if kind == "internal" else external).add(value)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = _resolve_relative_base(
                    module_id, is_package=is_package, level=node.level
                )
                if node.module:
                    candidate = ".".join((*base, *node.module.split(".")))
                    if candidate in all_modules or any(
                        module.startswith(candidate + ".") for module in all_modules
                    ):
                        internal.add(candidate)
                    else:
                        unresolved.add(f"(relative) {'.' * node.level}{node.module}")
                else:
                    for alias in node.names:
                        candidate = ".".join((*base, alias.name))
                        if candidate in all_modules or any(
                            module.startswith(candidate + ".") for module in all_modules
                        ):
                            internal.add(candidate)
                        else:
                            unresolved.add(f"(relative) {'.' * node.level}{alias.name}")
            elif node.module:
                add(node.module)
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in {"import_module", "__import__"}:
                dynamic = True

    return (
        tuple(sorted(internal)),
        tuple(sorted(external)),
        tuple(sorted(unresolved)),
        dynamic,
    )


def _entrypoint_paths(repo_root: Path) -> frozenset[str]:
    paths: set[str] = set()
    if (repo_root / "main.py").is_file():
        paths.add("main.py")
    scripts = repo_root / "scripts"
    if scripts.is_dir():
        paths.update(
            path.relative_to(repo_root).as_posix()
            for path in scripts.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    return frozenset(paths)


def _seed_imports(repo_root: Path, paths: Iterable[str], all_modules: frozenset[str]) -> set[str]:
    seeds: set[str] = set()
    for rel in paths:
        absolute = repo_root / rel
        if not absolute.is_file():
            continue
        try:
            tree = ast.parse(absolute.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        module_id = _path_to_module(rel) if rel.endswith(".py") else rel
        internal, _, _, _ = _extract_imports(
            tree,
            module_id=module_id,
            is_package=rel.endswith("/__init__.py"),
            all_modules=all_modules,
        )
        seeds.update(name for name in internal if name in all_modules)
    return seeds


def _reachable(records: Mapping[str, dict], seeds: set[str]) -> set[str]:
    live = {seed for seed in seeds if seed in records}
    stack = list(live)
    while stack:
        current = stack.pop()
        for imported in records[current]["internal_imports"]:
            if imported in records and imported not in live:
                live.add(imported)
                stack.append(imported)
    return live


def build_repository_inventory(repo_root: str | Path) -> RepositoryInventory:
    root = Path(repo_root).resolve()
    roots = _first_party_roots(root)
    files = _iter_python_files(root, roots)
    all_modules = frozenset(_path_to_module(path) for path in files)
    entrypoints = _entrypoint_paths(root)

    working: dict[str, dict] = {}
    for rel in files:
        data = (root / rel).read_bytes()
        module_id = _path_to_module(rel)
        record = {
            "module_id": module_id,
            "path": rel,
            "package": rel.split("/", 1)[0],
            "sha256": _sha256(data),
            "git_blob_sha": _git_blob_sha(data),
            "loc": data.count(b"\n") + (0 if not data or data.endswith(b"\n") else 1),
            "doc": None,
            "classes": (),
            "public_functions": (),
            "internal_imports": (),
            "external_imports": (),
            "unresolved_imports": (),
            "imported_by": [],
            "is_entrypoint": rel in entrypoints,
            "entrypoint_reachable": False,
            "test_reachable": False,
            "uses_dynamic_import": False,
            "parse_error": None,
        }
        try:
            tree = ast.parse(data.decode("utf-8", "replace"))
            doc = ast.get_docstring(tree)
            record["doc"] = doc.strip().splitlines()[0][:200] if doc else None
            record["classes"] = tuple(sorted(
                node.name for node in tree.body if isinstance(node, ast.ClassDef)
            ))
            record["public_functions"] = tuple(sorted(
                node.name for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not node.name.startswith("_")
            ))
            internal, external, unresolved, dynamic = _extract_imports(
                tree,
                module_id=module_id,
                is_package=rel.endswith("/__init__.py"),
                all_modules=all_modules,
            )
            record["internal_imports"] = internal
            record["external_imports"] = external
            record["unresolved_imports"] = unresolved
            record["uses_dynamic_import"] = dynamic
        except SyntaxError as exc:
            record["parse_error"] = f"{type(exc).__name__}: {exc}"
        working[module_id] = record

    for module_id, record in working.items():
        for imported in record["internal_imports"]:
            if imported in working:
                working[imported]["imported_by"].append(module_id)
    for record in working.values():
        record["imported_by"] = tuple(sorted(record["imported_by"]))

    entry_seeds = _seed_imports(root, entrypoints, all_modules)
    test_paths = tuple(
        path.relative_to(root).as_posix()
        for path in sorted((root / "tests").rglob("*.py"))
    ) if (root / "tests").is_dir() else ()
    test_seeds = _seed_imports(root, test_paths, all_modules)
    entry_live = _reachable(working, entry_seeds)
    test_live = _reachable(working, test_seeds)

    records: list[RepositoryModuleRecord] = []
    for module_id in sorted(working):
        raw = working[module_id]
        raw["entrypoint_reachable"] = module_id in entry_live
        raw["test_reachable"] = module_id in test_live
        records.append(RepositoryModuleRecord(**raw))

    digest_payload = [
        {
            "module_id": record.module_id,
            "path": record.path,
            "sha256": record.sha256,
            "classes": record.classes,
            "public_functions": record.public_functions,
            "internal_imports": record.internal_imports,
            "imported_by": record.imported_by,
            "is_entrypoint": record.is_entrypoint,
            "entrypoint_reachable": record.entrypoint_reachable,
            "test_reachable": record.test_reachable,
            "uses_dynamic_import": record.uses_dynamic_import,
            "parse_error": record.parse_error,
        }
        for record in records
    ]
    return RepositoryInventory(
        schema_version=INVENTORY_SCHEMA_VERSION,
        content_digest=_sha256(_canonical_json(digest_payload).encode("utf-8")),
        records=tuple(records),
    )


def _owned_records(
    capability: CapabilityRecord,
    inventory: RepositoryInventory,
) -> tuple[RepositoryModuleRecord, ...]:
    selected: list[RepositoryModuleRecord] = []
    for record in inventory.records:
        target = Path(record.path)
        for owned in capability.ownership_paths:
            owner = Path(owned)
            if target == owner:
                selected.append(record)
                break
            try:
                target.relative_to(owner)
            except ValueError:
                continue
            selected.append(record)
            break
    return tuple(sorted(selected, key=lambda record: record.path))


def capability_structural_fingerprints(
    *, catalog: CapabilityCatalog, inventory: RepositoryInventory
) -> tuple[CapabilityStructuralFingerprint, ...]:
    fingerprints: list[CapabilityStructuralFingerprint] = []
    for capability in sorted(catalog.capabilities, key=lambda item: item.capability_id):
        records = _owned_records(capability, inventory)
        payload = [
            {
                "path": record.path,
                "sha256": record.sha256,
                "classes": record.classes,
                "public_functions": record.public_functions,
                "internal_imports": record.internal_imports,
            }
            for record in records
        ]
        fingerprints.append(
            CapabilityStructuralFingerprint(
                capability_id=capability.capability_id,
                owned_module_paths=tuple(record.path for record in records),
                structural_fingerprint=_sha256(_canonical_json(payload).encode("utf-8")),
            )
        )
    return tuple(fingerprints)


def structural_search_text(
    *, capability: CapabilityRecord, inventory: RepositoryInventory
) -> str:
    """Derived structural terms for the existing semantic preflight scorer."""
    terms: list[str] = []
    for record in _owned_records(capability, inventory):
        terms.extend((record.module_id, record.path, record.doc or ""))
        terms.extend(record.classes)
        terms.extend(record.public_functions)
        terms.extend(record.internal_imports)
        terms.extend(record.imported_by)
    return " ".join(terms)
