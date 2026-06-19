from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR
from knowledge_domains.health.knowledge_manufacturing.knowledge_manufacturing_models import ConceptReviewItem, utc_now


class ConceptReviewQueue:
    """
    Human-in-the-loop queue for new or uncertain concepts.

    Items here are not errors. They are learning opportunities for the Factory.
    """

    VERSION = "0.1"

    def __init__(self, queue_path: Path | None = None):
        self.queue_path = queue_path or (BASE_DIR / "knowledge" / "factory" / "concept_review_queue" / "concept_review_queue.json")

    def append_items(self, items: list[ConceptReviewItem]) -> dict[str, Any]:
        existing = self.load()
        by_id = {item.get("review_id"): item for item in existing.get("items", [])}
        added = 0
        for item in items:
            payload = asdict(item)
            if payload["review_id"] not in by_id:
                by_id[payload["review_id"]] = payload
                added += 1
        queue = {
            "queue_type": "concept_review_queue",
            "queue_version": self.VERSION,
            "updated_at": utc_now(),
            "item_count": len(by_id),
            "pending_count": sum(1 for item in by_id.values() if item.get("status") == "pending_human_review"),
            "items": list(by_id.values()),
        }
        self.write(queue)
        return {"added_count": added, "item_count": queue["item_count"], "pending_count": queue["pending_count"], "path": str(self.queue_path.relative_to(BASE_DIR)).replace("\\", "/")}

    def load(self) -> dict[str, Any]:
        if not self.queue_path.exists():
            return {"queue_type": "concept_review_queue", "queue_version": self.VERSION, "items": []}
        with self.queue_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def write(self, payload: dict[str, Any]) -> None:
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        with self.queue_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
