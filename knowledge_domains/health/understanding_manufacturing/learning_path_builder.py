"""Learning Path Builder v1.0."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from factory_sdk import stable_hash

from .learning_path_models import LearningPath, LearningPathStep
from .learning_path_templates import LearningPathTemplate, STANDARD_LEARNING_PATH_TEMPLATES


class LearningPathBuilder:
    """Builds deterministic Learning Paths from Learning Primitive Collections."""

    def __init__(self, *, rules_version: str) -> None:
        self.rules_version = rules_version

    def build_paths(self, primitive_collection: Dict[str, Any]) -> List[LearningPath]:
        primitives = primitive_collection.get("primitives", [])
        primitive_index = self._index_primitives(primitives)
        paths: List[LearningPath] = []
        for template in STANDARD_LEARNING_PATH_TEMPLATES:
            path = self._build_path_from_template(primitive_collection, primitive_index, template)
            paths.append(path)
        return paths

    def _build_path_from_template(
        self,
        primitive_collection: Dict[str, Any],
        primitive_index: Dict[str, Dict[str, Any]],
        template: LearningPathTemplate,
    ) -> LearningPath:
        concept_id = primitive_collection["concept_id"]
        concept_name = primitive_collection["concept_name"]
        warnings: List[str] = []
        steps: List[LearningPathStep] = []

        for primitive_type in template.primitive_sequence:
            primitive = primitive_index.get(primitive_type)
            if primitive:
                steps.append(self._step(len(steps) + 1, primitive, mandatory=True))
            else:
                warnings.append(f"Missing mandatory primitive type for path {template.path_type}: {primitive_type}")

        for primitive_type in template.optional_primitive_sequence:
            primitive = primitive_index.get(primitive_type)
            if primitive and primitive.get("primitive_id") not in {step.primitive_id for step in steps}:
                steps.append(self._step(len(steps) + 1, primitive, mandatory=False))

        path_id = stable_hash(
            {
                "concept_id": concept_id,
                "path_type": template.path_type,
                "ordered_primitive_ids": [step.primitive_id for step in steps],
                "rules_version": self.rules_version,
            },
            prefix="lpath",
        )

        return LearningPath(
            path_id=path_id,
            path_type=template.path_type,
            path_name=template.path_name,
            concept_id=concept_id,
            concept_name=concept_name,
            learning_goal=template.learning_goal,
            target_persona=template.target_persona,
            delivery_context=template.delivery_context,
            estimated_duration_seconds=template.estimated_duration_seconds,
            difficulty=template.difficulty,
            steps=steps,
            success_criteria=template.success_criteria,
            recommended_next_paths=template.recommended_next_paths,
            tags=template.tags,
            warnings=warnings,
        )

    @staticmethod
    def _step(step_number: int, primitive: Dict[str, Any], *, mandatory: bool) -> LearningPathStep:
        return LearningPathStep(
            step_number=step_number,
            primitive_id=primitive["primitive_id"],
            primitive_type=primitive["primitive_type"],
            mandatory=mandatory,
            learning_objective=primitive.get("learning_objective", ""),
        )

    @staticmethod
    def _index_primitives(primitives: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        # One primitive per type for v1.0. If multiple appear later, the first stable sorted primitive wins.
        ordered = sorted(primitives, key=lambda p: (p.get("primitive_type", ""), p.get("primitive_id", "")))
        index: Dict[str, Dict[str, Any]] = {}
        for primitive in ordered:
            primitive_type = primitive.get("primitive_type")
            if primitive_type and primitive_type not in index:
                index[primitive_type] = primitive
        return index
