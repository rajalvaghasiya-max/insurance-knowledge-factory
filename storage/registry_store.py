import json
from pathlib import Path
from typing import Any


def load_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = []

    if not path.exists():
        return default

    if path.stat().st_size == 0:
        return default

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)