from dataclasses import dataclass, field
from typing import List


@dataclass
class GMVSValidationResult:
    name: str
    status: str
    score: int
    notes: List[str] = field(default_factory=list)


@dataclass
class GMVSScorecard:
    concept_id: str
    concept_name: str

    architecture_reuse_percent: int
    department_reuse_percent: int
    infrastructure_reuse_percent: int

    architecture_changes_required: int
    new_infrastructure_files: int
    concept_specific_code_files: int
    fer_entries_generated: int

    factory_stability_score: int
    factory_maturity: str
    manufacturing_status: str
    overall_rating: str


@dataclass
class GMVSReport:
    report_id: str
    concept_id: str
    concept_name: str
    version: str
    factory_version: str
    validation_scope: str

    architecture_validation: GMVSValidationResult
    readiness_validation: GMVSValidationResult
    manufacturing_validation: GMVSValidationResult
    reuse_analysis: GMVSValidationResult
    governance_validation: GMVSValidationResult

    scorecard: GMVSScorecard
    recommendations: List[str]

    certification_status: str
    created_at: str