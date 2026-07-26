from __future__ import annotations

from typing import Dict, List

from .execution_models import ExecutionLog


class OutputCollector:
    def collect(self, execution_log: ExecutionLog) -> Dict[str, List[str]]:
        outputs: Dict[str, List[str]] = {}
        for result in execution_log.results:
            if result.status != "PASS":
                continue
            outputs.setdefault(result.asset_type, []).extend(result.output_paths.values())
        return {key: sorted(value) for key, value in sorted(outputs.items())}
