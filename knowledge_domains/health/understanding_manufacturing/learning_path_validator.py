"""Learning Path Validator v1.0."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


class LearningPathValidator:
    """Validates Learning Path Collections without adding business interpretation."""

    def validate(self, primitive_collection: Dict[str, Any], path_collection: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        warnings: List[str] = []
        errors: List[str] = []

        primitive_ids = {p.get("primitive_id") for p in primitive_collection.get("primitives", [])}
        paths = path_collection.get("paths", [])
        if not paths:
            errors.append("Learning Path Collection has no paths.")
            return warnings, errors

        for path in paths:
            self._validate_path(path, primitive_ids, warnings, errors)

        path_types = {path.get("path_type") for path in paths}
        required_path_types = {
            "quick_understanding",
            "claim_understanding",
            "buying_decision",
            "advisor_teaching",
            "deep_learning",
        }
        missing = sorted(required_path_types - path_types)
        if missing:
            errors.append(f"Missing standard learning paths: {missing}")

        return warnings, errors

    def _validate_path(
        self,
        path: Dict[str, Any],
        primitive_ids: set,
        warnings: List[str],
        errors: List[str],
    ) -> None:
        path_type = path.get("path_type", "unknown")
        if not path.get("learning_goal"):
            errors.append(f"Path missing learning_goal: {path_type}")
        if not path.get("target_persona"):
            errors.append(f"Path missing target_persona: {path_type}")
        if not path.get("success_criteria"):
            warnings.append(f"Path missing success_criteria: {path_type}")

        steps = path.get("steps", [])
        if not steps:
            errors.append(f"Path has no steps: {path_type}")
            return

        seen_primitives = set()
        expected_step = 1
        for step in steps:
            if step.get("step_number") != expected_step:
                errors.append(f"Path {path_type} has invalid step order at step {step.get('step_number')}")
            expected_step += 1

            primitive_id = step.get("primitive_id")
            if primitive_id not in primitive_ids:
                errors.append(f"Path {path_type} references unknown primitive: {primitive_id}")
            if primitive_id in seen_primitives:
                errors.append(f"Path {path_type} has duplicate primitive reference: {primitive_id}")
            seen_primitives.add(primitive_id)

            if not step.get("learning_objective"):
                warnings.append(f"Path {path_type} step missing learning objective: {primitive_id}")
