from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ARCHIVE_DIR = BASE_DIR / "archive"

RAW_HTML_DIR = ARCHIVE_DIR / "raw_html"
SCREENSHOT_DIR = ARCHIVE_DIR / "screenshots"
DOCUMENTS_DIR = ARCHIVE_DIR / "documents"
METADATA_DIR = ARCHIVE_DIR / "metadata"
TEXT_DIR = ARCHIVE_DIR / "text"

REGISTRY_DIR = BASE_DIR / "registry"

PDF_REGISTRY_PATH = REGISTRY_DIR / "pdf_registry.json"
INSURER_REGISTRY_PATH = REGISTRY_DIR / "insurers.json"
SOURCE_REGISTRY_PATH = REGISTRY_DIR / "source_registry.json"

USER_AGENT = "PolicyScna-Insurance-Knowledge-Factory/0.1"

REQUEST_TIMEOUT = 20