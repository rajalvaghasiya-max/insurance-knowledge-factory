"""Learning Path Builder v1.0."""

from __future__ import annotations

from dataclasses import replace
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

        # A buying-decision path is valid only when an explicitly governed
        # suitability primitive exists. Generic concept education must not
        # manufacture recommendation-layer curriculum by implication.
        templates = [
            template
            for template in STANDARD_LEARNING_PATH_TEMPLATES
            if template.path_type != "buying_decision"
            or "suitability" in primitive_index
        ]
        allowed_path_types = {template.path_type for template in templates}

        paths: List[LearningPath] = []
        for template in templates:
            path = self._build_path_from_template(
                primitive_collection,
                primitive_index,
                template,
            )
            path = replace(
                path,
                recommended_next_paths=[
                    path_type
                    for path_type in path.recommended_next_paths
                    if path_type in allowed_path_types
                ],
            )
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

        soft_optional_types = {
            "suitability",
            "advisor_note",
            "source_example",
        }

        for primitive_type in template.primitive_sequence:
            primitive = primitive_index.get(primitive_type)
            if primitive:
                steps.append(self._step(len(steps) + 1, primitive, mandatory=True))
            elif primitive_type not in soft_optional_types:
                warnings.append(
                    f"Missing mandatory primitive type for path "
                    f"{template.path_type}: {primitive_type}"
                )

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

        success_criteria = list(template.success_criteria)
        if "suitability" not in primitive_index:
            success_criteria = [
                criterion.replace(
                    "define, explain, calculate, compare, and teach",
                    "define, explain, calculate, and teach",
                )
                for criterion in success_criteria
            ]

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
            success_criteria=success_criteria,
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

