"""
PolicyScna Department V — Learning Primitive Manufacturing Line v1.0

Consumes:
    meaning_asset

Manufactures:
    learning_primitive_collection

Boundary:
    Manufactures modular learning primitives only. It does not personalize,
    recommend, or generate final user-facing conversations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from factory_sdk import (
    CertificationResult,
    CertificationStatus,
    FactoryProductionLine,
    ProductionLineContract,
    QualityWarning,
    stable_hash,
)

from .learning_primitive_models import LearningPrimitive, LearningPrimitiveCollection


DEPARTMENT_BOUNDARY = "meaning_to_learning_primitives_only_no_personalized_advice"


class LearningPrimitiveManufacturingLine(FactoryProductionLine):
    """Manufactures Learning Primitive Collections from Meaning Assets."""

    contract = ProductionLineContract(
        engine_name="LearningPrimitiveManufacturingLine",
        department="department_05_understanding_manufacturing",
        production_line="learning_primitive_manufacturing",
        consumes="meaning_asset",
        manufactures="learning_primitive_collection",
        customer_department="understanding_asset_composition",
        engine_version="1.0",
        rules_version="learning_primitive_rules_v1.0",
        schema_version="learning_primitive_collection_v1.0",
        deterministic=True,
        certification_required=True,
        department_boundary=DEPARTMENT_BOUNDARY,
    )

    def validate_input(self, raw_input: Dict[str, Any]) -> None:
        super().validate_input(raw_input)
        if raw_input.get("asset_type") != self.contract.consumes:
            raise ValueError(
                f"Expected input asset_type={self.contract.consumes}, got {raw_input.get('asset_type')}"
            )
        if not raw_input.get("concept_id"):
            raise ValueError("Meaning asset must include concept_id.")
        if not raw_input.get("canonical_name"):
            raise ValueError("Meaning asset must include canonical_name.")

    def manufacture(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        concept_id = raw_input["concept_id"]
        concept_name = raw_input["canonical_name"]
        evidence_refs = self._collect_evidence_refs(raw_input)

        primitives = self._build_primitives(raw_input, evidence_refs)
        payload_for_id = {
            "concept_id": concept_id,
            "source_meaning_asset_id": raw_input.get("asset_id"),
            "rules_version": self.contract.rules_version,
            "primitives": [primitive.to_dict() for primitive in primitives],
        }
        asset_id = stable_hash(payload_for_id, prefix="lpc")

        collection = LearningPrimitiveCollection(
            asset_id=asset_id,
            asset_type=self.contract.manufactures,
            collection_id=asset_id,
            collection_version="1.0",
            schema_version=self.contract.schema_version,
            department_boundary=self.contract.department_boundary,
            concept_id=concept_id,
            concept_name=concept_name,
            source_meaning_asset_id=raw_input.get("asset_id", "unknown"),
            source_meaning_asset_type=raw_input.get("asset_type", "unknown"),
            primitives=primitives,
            notes=[
                "Learning Primitives are modular educational units.",
                "No personalized advice or final customer conversation is manufactured in this asset.",
            ],
        )
        return collection.to_dict()

    def _build_primitives(
        self,
        meaning: Dict[str, Any],
        evidence_refs: List[str],
    ) -> List[LearningPrimitive]:
        concept_id = meaning["concept_id"]
        governance = meaning.get("governance", {})
        is_governed_generic_concept = (
            isinstance(governance, dict)
            and bool(governance.get("source_governed_record_id"))
        )
        if concept_id == "copay" and not is_governed_generic_concept:
            return self._build_copay_primitives(meaning, evidence_refs)
        return self._build_generic_primitives(meaning, evidence_refs)

    def _primitive(
        self,
        *,
        concept_id: str,
        concept_name: str,
        primitive_type: str,
        learning_objective: str,
        content: Dict[str, Any],
        delivery_tags: List[str],
        evidence_refs: List[str],
        source_meaning_fields: List[str],
        difficulty: str = "basic",
        prerequisites: List[str] | None = None,
        confidence: float = 1.0,
    ) -> LearningPrimitive:
        primitive_id = stable_hash(
            {
                "concept_id": concept_id,
                "primitive_type": primitive_type,
                "learning_objective": learning_objective,
                "content": content,
                "rules_version": self.contract.rules_version,
            },
            prefix="lp",
        )
        return LearningPrimitive(
            primitive_id=primitive_id,
            primitive_type=primitive_type,
            concept_id=concept_id,
            concept_name=concept_name,
            learning_objective=learning_objective,
            content=content,
            delivery_tags=delivery_tags,
            difficulty=difficulty,
            prerequisites=prerequisites or [],
            evidence_refs=evidence_refs,
            source_meaning_fields=source_meaning_fields,
            confidence=confidence,
        )

    def _build_copay_primitives(self, meaning: Dict[str, Any], evidence_refs: List[str]) -> List[LearningPrimitive]:
        concept_id = meaning["concept_id"]
        concept_name = meaning["canonical_name"]
        relationships = meaning.get("relationships", {})
        related = sorted(set(relationships.get("related_to", []) + relationships.get("commonly_confused_with", [])))
        examples = meaning.get("policy_examples", [])

        primitives = [
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="definition",
                learning_objective="Customer should be able to define Copay.",
                content={
                    "text": "Copay means you agree to pay a fixed percentage of every approved insurance claim.",
                    "canonical_meaning": meaning.get("core_meaning"),
                },
                delivery_tags=["consumer", "advisor", "comparison", "learning"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["core_meaning", "calculation_basis"],
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="meaning",
                learning_objective="Customer understands that Copay is calculated after claim review.",
                content={
                    "text": "Insurance companies first determine how much of your hospital bill is payable under your policy. Only after that is Copay calculated.",
                    "calculation_basis": meaning.get("calculation_basis"),
                },
                delivery_tags=["consumer", "advisor", "claim", "learning"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["calculation_basis", "functional_behaviour"],
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="money_flow",
                learning_objective="Customer understands who pays what during a Copay claim.",
                content={
                    "steps": [
                        "Hospital Bill",
                        "Claim Review",
                        "Approved Amount",
                        "Apply Copay",
                        "Insurance Pays Remaining Approved Amount",
                        "Customer Pays Non-payable Items plus Copay",
                    ],
                    "visual_hint": "money_flow_diagram",
                },
                delivery_tags=["consumer", "advisor", "claim", "visual"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["inputs", "outputs", "functional_behaviour"],
                difficulty="intermediate",
                prerequisites=["approved_claim_amount"],
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="worked_example",
                learning_objective="Customer can calculate Copay correctly using approved claim amount.",
                content={
                    "currency": "INR",
                    "hospital_bill": 100000,
                    "approved_claim_amount": 90000,
                    "non_payable_amount": 10000,
                    "copay_percentage": 20,
                    "copay_amount": 18000,
                    "customer_pays_total": 28000,
                    "insurer_pays": 72000,
                    "formula": "customer_pays_total = non_payable_amount + (approved_claim_amount * copay_percentage)",
                    "explanation": "20% is applied on ₹90,000, not on ₹1,00,000. The ₹10,000 non-payable amount is added separately.",
                },
                delivery_tags=["consumer", "advisor", "claim", "calculation"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["inputs", "outputs", "calculation_basis"],
                difficulty="intermediate",
                prerequisites=["approved_claim_amount", "non_payable_amount"],
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="misconception",
                learning_objective="Customer avoids the common incorrect expectation that Copay is the only amount payable.",
                content={
                    "misconception": "Copay means I pay only 20% of the total hospital bill.",
                    "correction": "Copay is calculated on the insurer-approved amount. Expenses not payable under the policy are paid separately.",
                    "source_misinterpretations": meaning.get("misinterpretations", []),
                },
                delivery_tags=["consumer", "advisor", "claim", "warning"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["misinterpretations", "calculation_basis"],
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="purpose",
                learning_objective="Customer understands why Copay exists.",
                content={
                    "text": "Policies with Copay usually cost less because the customer shares a portion of every claim.",
                    "business_purpose": meaning.get("business_purpose"),
                },
                delivery_tags=["consumer", "advisor", "comparison", "recommendation"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["business_purpose"],
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="suitability",
                learning_objective="Customer understands when a Copay policy may or may not be suitable.",
                content={
                    "may_be_suitable_when": [
                        "Customer wants lower premium.",
                        "Customer is comfortable sharing claim costs.",
                    ],
                    "may_not_be_suitable_when": [
                        "Customer wants predictable claim payout.",
                        "Customer may not be comfortable paying during hospitalization.",
                    ],
                    "boundary": "This is not a recommendation. Final suitability depends on customer context.",
                },
                delivery_tags=["advisor", "comparison", "recommendation"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["business_purpose", "constraints"],
                difficulty="intermediate",
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="related_concepts",
                learning_objective="Customer can connect Copay with nearby insurance concepts.",
                content={"related_concepts": related},
                delivery_tags=["consumer", "advisor", "learning"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["relationships"],
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="faq",
                learning_objective="Customer can answer whether they will always pay only the Copay percentage.",
                content={
                    "question": "Will I always pay only the Copay percentage?",
                    "answer": "No. You may also pay expenses that are not covered by the policy.",
                },
                delivery_tags=["consumer", "advisor", "claim", "faq"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["misinterpretations", "outputs"],
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="advisor_note",
                learning_objective="Advisor understands how to explain Copay clearly.",
                content={
                    "text": "Always explain Copay using an actual claim example. Customers rarely misunderstand the definition; they misunderstand the calculation.",
                    "recommended_primitives": ["money_flow", "worked_example", "misconception"],
                },
                delivery_tags=["advisor"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["misinterpretations", "policy_examples"],
                difficulty="advisor",
            ),
        ]

        # Preserve any source policy examples without making them final explanations.
        if examples:
            primitives.append(
                self._primitive(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    primitive_type="source_example",
                    learning_objective="Advisor can trace the learning primitive back to the source meaning example.",
                    content={"policy_examples": examples},
                    delivery_tags=["advisor", "audit"],
                    evidence_refs=evidence_refs,
                    source_meaning_fields=["policy_examples"],
                    difficulty="advisor",
                )
            )
        return primitives

    def _build_generic_primitives(
        self,
        meaning: Dict[str, Any],
        evidence_refs: List[str],
    ) -> List[LearningPrimitive]:
        """Build field-driven primitives for any governed meaning asset.

        This path restructures only content already present in the meaning asset.
        It does not add personalized advice, suitability judgments,
        recommendations, claim decisions, or final customer-facing answers.
        """
        concept_id = meaning["concept_id"]
        concept_name = meaning["canonical_name"]
        confidence_value = (
            float(meaning.get("confidence", {}).get("canonical_confidence", 0.8))
            if isinstance(meaning.get("confidence"), dict)
            else 0.8
        )

        primitives: List[LearningPrimitive] = [
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="definition",
                learning_objective=f"Customer should be able to define {concept_name}.",
                content={
                    "text": meaning.get("core_meaning", ""),
                    "canonical_meaning": meaning.get("core_meaning", ""),
                },
                delivery_tags=["consumer", "advisor", "learning"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["core_meaning"],
                confidence=confidence_value,
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="meaning",
                learning_objective=(
                    f"Customer understands how {concept_name} operates under policy terms."
                ),
                content={
                    "text": meaning.get("functional_behaviour", ""),
                    "calculation_basis": meaning.get("calculation_basis"),
                    "trigger": meaning.get("trigger"),
                },
                delivery_tags=["consumer", "advisor", "claim", "learning"],
                evidence_refs=evidence_refs,
                source_meaning_fields=[
                    "functional_behaviour",
                    "calculation_basis",
                    "trigger",
                ],
                confidence=confidence_value,
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="purpose",
                learning_objective=f"Customer understands why {concept_name} exists.",
                content={
                    "text": meaning.get("business_purpose", ""),
                    "business_purpose": meaning.get("business_purpose", ""),
                },
                delivery_tags=["consumer", "advisor", "learning"],
                evidence_refs=evidence_refs,
                source_meaning_fields=["business_purpose"],
                confidence=confidence_value,
            ),
            self._primitive(
                concept_id=concept_id,
                concept_name=concept_name,
                primitive_type="money_flow",
                learning_objective=(
                    f"Customer understands the sequence in which {concept_name} "
                    "affects eligible insurer assessment."
                ),
                content={
                    "inputs": meaning.get("inputs", []),
                    "outputs": meaning.get("outputs", []),
                    "functional_behaviour": meaning.get(
                        "functional_behaviour", ""
                    ),
                    "visual_hint": "process_flow_diagram",
                },
                delivery_tags=["consumer", "advisor", "claim", "visual"],
                evidence_refs=evidence_refs,
                source_meaning_fields=[
                    "inputs",
                    "outputs",
                    "functional_behaviour",
                ],
                difficulty="intermediate",
                confidence=confidence_value,
            ),
        ]

        examples = meaning.get("policy_examples", [])
        if isinstance(examples, list) and examples:
            primitives.append(
                self._primitive(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    primitive_type="worked_example",
                    learning_objective=(
                        f"Customer can follow a governed example of {concept_name}."
                    ),
                    content={
                        "policy_examples": examples,
                        "calculation_basis": meaning.get("calculation_basis"),
                    },
                    delivery_tags=[
                        "consumer",
                        "advisor",
                        "claim",
                        "calculation",
                    ],
                    evidence_refs=evidence_refs,
                    source_meaning_fields=[
                        "policy_examples",
                        "calculation_basis",
                        "inputs",
                        "outputs",
                    ],
                    difficulty="intermediate",
                    confidence=confidence_value,
                )
            )

        misinterpretations = meaning.get("misinterpretations", [])
        if isinstance(misinterpretations, list) and misinterpretations:
            primitives.append(
                self._primitive(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    primitive_type="misconception",
                    learning_objective=(
                        f"Customer avoids common misunderstandings about "
                        f"{concept_name}."
                    ),
                    content={
                        "source_misinterpretations": misinterpretations,
                        "canonical_meaning": meaning.get("core_meaning", ""),
                    },
                    delivery_tags=[
                        "consumer",
                        "advisor",
                        "claim",
                        "warning",
                    ],
                    evidence_refs=evidence_refs,
                    source_meaning_fields=[
                        "misinterpretations",
                        "core_meaning",
                    ],
                    confidence=confidence_value,
                )
            )

        relationships = meaning.get("relationships", {})
        related: List[str] = []
        if isinstance(relationships, dict):
            for key in (
                "related_to",
                "commonly_confused_with",
                "depends_on",
                "subset",
            ):
                value = relationships.get(key, [])
                if isinstance(value, list):
                    related.extend(str(item) for item in value)
                elif isinstance(value, str):
                    related.append(value)
        related = sorted(set(item for item in related if item))
        if related:
            primitives.append(
                self._primitive(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    primitive_type="related_concepts",
                    learning_objective=(
                        f"Customer can connect {concept_name} with nearby "
                        "insurance concepts."
                    ),
                    content={
                        "related_concepts": related,
                        "source_relationships": relationships,
                    },
                    delivery_tags=["consumer", "advisor", "learning"],
                    evidence_refs=evidence_refs,
                    source_meaning_fields=["relationships"],
                    confidence=confidence_value,
                )
            )

        constraints = meaning.get("constraints", [])
        exceptions = meaning.get("exceptions", [])
        if constraints or exceptions:
            primitives.append(
                self._primitive(
                    concept_id=concept_id,
                    concept_name=concept_name,
                    primitive_type="faq",
                    learning_objective=(
                        f"Customer understands the boundaries of {concept_name}."
                    ),
                    content={
                        "question": (
                            f"Does {concept_name} always work the same way?"
                        ),
                        "answer": (
                            "No. The applicable policy wording, schedule, "
                            "admissibility, limits, and documented exceptions "
                            "must be checked."
                        ),
                        "constraints": constraints,
                        "exceptions": exceptions,
                    },
                    delivery_tags=[
                        "consumer",
                        "advisor",
                        "claim",
                        "faq",
                    ],
                    evidence_refs=evidence_refs,
                    source_meaning_fields=["constraints", "exceptions"],
                    confidence=confidence_value,
                )
            )

        return primitives
    def quality_check(
        self, raw_input: Dict[str, Any], manufactured_asset: Dict[str, Any]
    ) -> Tuple[float, List[QualityWarning], List[str]]:
        quality_score, warnings, errors = super().quality_check(raw_input, manufactured_asset)
        primitives = manufactured_asset.get("primitives", [])

        if not primitives:
            errors.append("Learning Primitive Collection has no primitives.")
            quality_score = 0.0

        missing_objectives = [p.get("primitive_id", "unknown") for p in primitives if not p.get("learning_objective")]
        if missing_objectives:
            errors.append(f"Primitives missing learning objectives: {missing_objectives}")
            quality_score = min(quality_score, 60.0)

        missing_content = [p.get("primitive_id", "unknown") for p in primitives if not p.get("content")]
        if missing_content:
            errors.append(f"Primitives missing content: {missing_content}")
            quality_score = min(quality_score, 60.0)

        missing_traceability = [
            p.get("primitive_id", "unknown")
            for p in primitives
            if not p.get("evidence_refs") and not p.get("source_meaning_fields")
        ]
        if missing_traceability:
            errors.append(f"Primitives missing traceability: {missing_traceability}")
            quality_score = min(quality_score, 70.0)

        governance = raw_input.get("governance", {})
        is_governed_generic_concept = (
            isinstance(governance, dict)
            and bool(governance.get("source_governed_record_id"))
        )

        if (
            raw_input.get("concept_id") == "copay"
            and not is_governed_generic_concept
            and len(primitives) < 10
        ):
            warnings.append(
                QualityWarning(
                    type="golden_concept_coverage",
                    severity="medium",
                    message=(
                        "Legacy Copay golden concept should normally produce "
                        "at least 10 primitives."
                    ),
                )
            )
            quality_score = min(quality_score, 90.0)
        if is_governed_generic_concept and len(primitives) < 6:
            errors.append(
                "Governed generic concept meaning assets must manufacture at least "
                "6 traceable learning primitives."
            )
            quality_score = min(quality_score, 60.0)

        return quality_score, warnings, errors

    def certify(self, raw_input: Dict[str, Any], manufactured_asset: Dict[str, Any]) -> CertificationResult:
        certification = super().certify(raw_input, manufactured_asset)
        gates_passed = list(certification.gates_passed)
        gates_failed = list(certification.gates_failed)
        errors = list(certification.errors)
        warnings = list(certification.warnings)

        primitives = manufactured_asset.get("primitives", [])
        if all(p.get("learning_objective") for p in primitives):
            gates_passed.append("learning_objectives_present")
        else:
            gates_failed.append("learning_objectives_present")

        if all(p.get("content") for p in primitives):
            gates_passed.append("primitive_content_present")
        else:
            gates_failed.append("primitive_content_present")

        if all(p.get("evidence_refs") or p.get("source_meaning_fields") for p in primitives):
            gates_passed.append("traceability_preserved")
        else:
            gates_failed.append("traceability_preserved")

        status = CertificationStatus.PASSED
        if errors or gates_failed:
            status = CertificationStatus.FAILED
        elif warnings or certification.quality_score < 90:
            status = CertificationStatus.NEEDS_REVIEW

        return CertificationResult(
            validation_status=status,
            quality_score=certification.quality_score,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            warnings=warnings,
            errors=errors,
        )

    def build_statistics(
        self,
        raw_input: Dict[str, Any],
        manufactured_asset: Dict[str, Any],
        certification: CertificationResult,
    ) -> Dict[str, Any]:
        base = super().build_statistics(raw_input, manufactured_asset, certification)
        primitives = manufactured_asset.get("primitives", [])
        primitive_type_counts: Dict[str, int] = {}
        delivery_tag_counts: Dict[str, int] = {}
        for primitive in primitives:
            primitive_type = primitive.get("primitive_type", "unknown")
            primitive_type_counts[primitive_type] = primitive_type_counts.get(primitive_type, 0) + 1
            for tag in primitive.get("delivery_tags", []):
                delivery_tag_counts[tag] = delivery_tag_counts.get(tag, 0) + 1
        base.update(
            {
                "concept_id": manufactured_asset.get("concept_id"),
                "concept_name": manufactured_asset.get("concept_name"),
                "source_meaning_asset_id": manufactured_asset.get("source_meaning_asset_id"),
                "primitive_count": len(primitives),
                "primitive_type_counts": primitive_type_counts,
                "delivery_tag_counts": delivery_tag_counts,
            }
        )
        return base

    @staticmethod
    def _collect_evidence_refs(raw_input: Dict[str, Any]) -> List[str]:
        evidence = raw_input.get("evidence", [])
        refs: List[str] = []
        if isinstance(evidence, list):
            for item in evidence:
                if isinstance(item, dict):
                    refs.append(str(item.get("evidence_id") or item.get("reference_id") or item.get("source_id") or item))
                else:
                    refs.append(str(item))
        return sorted(set(refs))

