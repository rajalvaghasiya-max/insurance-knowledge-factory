from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .observation_models import ObservationRecord


class ObservationReader:
    """Reads an Observation Register JSON file into normalized observations."""

    def read_file(self, path: str | Path) -> List[ObservationRecord]:
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "observations" in data:
            rows = data["observations"]
        elif isinstance(data, list):
            rows = data
        else:
            raise ValueError("Observation register must be a list or an object with an 'observations' list.")

        return [ObservationRecord.from_dict(row) for row in rows]
