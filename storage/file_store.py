import hashlib
from pathlib import Path
from datetime import datetime, timezone


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_filename(value: str) -> str:
    cleaned = value.lower().strip()
    cleaned = cleaned.replace("https://", "")
    cleaned = cleaned.replace("http://", "")
    cleaned = cleaned.replace("/", "_")
    cleaned = cleaned.replace("\\", "_")
    cleaned = cleaned.replace("?", "_")
    cleaned = cleaned.replace("&", "_")
    cleaned = cleaned.replace("=", "_")
    cleaned = cleaned.replace(":", "_")
    return cleaned[:180]


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        file.write(content)

from pathlib import Path

def write_bytes_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "wb") as file:
        file.write(content)