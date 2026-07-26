from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


class DocumentLoaderEngine:
    """
    Department III — Document Processing
    Engine: Document Loader Engine

    Responsibility:
        Locate the source document described by a work order / registry record.

    This engine does not read, parse, or interpret document content.
    """

    VERSION = "0.1"

    def load(self, job: dict[str, Any]) -> dict[str, Any]:
        path_value = job.get("path")
        relative_path = job.get("relative_path")

        if path_value:
            path = Path(path_value)
        elif relative_path:
            path = BASE_DIR / relative_path
        else:
            raise ValueError("Job does not contain path or relative_path")

        if not path.exists():
            raise FileNotFoundError(f"Source document not found: {path}")
        if not path.is_file():
            raise ValueError(f"Source path is not a file: {path}")

        return {
            "path": path,
            "relative_path": relative_path or str(path.relative_to(BASE_DIR)).replace("\\", "/"),
            "suffix": path.suffix.lower(),
            "file_size_bytes": path.stat().st_size,
        }
