from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .architecture_validator import validate_architecture
from .governance_validator import validate_governance
from .gmvs_models import (
    GMVSReport,
    GMVSScorecard,
    GMVSValidationResult,
)
from .manufacturing_validator import validate_manufacturing
from .readiness_validator import validate_readiness
from .reuse_analyzer import analyze_reuse


class GMVSReportBuilder:
    """Assembles deterministic Factory-validation results into one GMVS report."""

    FACTORY_VERSION = "1.0"
    REPORT_VERSION = "1.0"

    BASELINE_SCOPE = "BASELINE"
    CROSS_CONCEPT_SCOPE = "CROSS_CONCEPT"

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def build(self, concept_id: str, concept_name: str | None = None) -> GMVSReport:
        concept_name = concept_name or concept_id.replace("_", " ").title()
        validation_scope = self.determine_validation_scope(concept_id)

        architecture = validate_architecture(self.repo_root)
        readiness = validate_readiness(self.repo_root, concept_id)
        manufacturing = validate_manufacturing(self.repo_root, concept_id)
        reuse = analyze_reuse(self.repo_root, concept_id)
        governance = validate_governance(self.repo_root)

        scorecard = self._build_scorecard(
            concept_id=concept_id,
            concept_name=concept_name,
            validation_scope=validation_scope,
            architecture=architecture,
            readiness=readiness,
            manufacturing=manufacturing,
            reuse=reuse,
            governance=governance,
        )

        recommendations = self._build_recommendations(
            validation_scope=validation_scope,
            architecture=architecture,
            readiness=readiness,
            manufacturing=manufacturing,
            reuse=reuse,
            governance=governance,
        )

        certification_status = self._overall_status(
            architecture,
            readiness,
            manufacturing,
            reuse,
            governance,
        )

        return GMVSReport(
            report_id=f"gmvs_{uuid4().hex[:24]}",
            concept_id=concept_id,
            concept_name=concept_name,
            version=self.REPORT_VERSION,
            factory_version=self.FACTORY_VERSION,
            validation_scope=validation_scope,
            architecture_validation=architecture,
            readiness_validation=readiness,
            manufacturing_validation=manufacturing,
            reuse_analysis=reuse,
            governance_validation=governance,
            scorecard=scorecard,
            recommendations=recommendations,
            certification_status=certification_status,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def determine_validation_scope(self, concept_id: str) -> str:
        gmvs_root = self.repo_root / "knowledge" / "factory" / "gmvs"

        if not gmvs_root.exists():
            return self.BASELINE_SCOPE

        other_concept_reports = [
            report_path
            for report_path in gmvs_root.glob("*/gmvs_report.json")
            if report_path.parent.name != concept_id
        ]

        if other_concept_reports:
            return self.CROSS_CONCEPT_SCOPE

        return self.BASELINE_SCOPE

    def _build_scorecard(
        self,
        *,
        concept_id: str,
        concept_name: str,
        validation_scope: str,
        architecture: GMVSValidationResult,
        readiness: GMVSValidationResult,
        manufacturing: GMVSValidationResult,
        reuse: GMVSValidationResult,
        governance: GMVSValidationResult,
    ) -> GMVSScorecard:
        scores = [
            architecture.score,
            readiness.score,
            manufacturing.score,
            reuse.score,
            governance.score,
        ]
        stability_score = int(sum(scores) / len(scores))

        return GMVSScorecard(
            concept_id=concept_id,
            concept_name=concept_name,
            architecture_reuse_percent=reuse.score,
            department_reuse_percent=reuse.score,
            infrastructure_reuse_percent=reuse.score,
            architecture_changes_required=0 if architecture.status == "PASS" else 1,
            new_infrastructure_files=0,
            concept_specific_code_files=0,
            fer_entries_generated=0,
            factory_stability_score=stability_score,
            factory_maturity=self._factory_maturity(
                score=stability_score,
                validation_scope=validation_scope,
            ),
            manufacturing_status=self._manufacturing_status(manufacturing),
            overall_rating=self._rating(
                score=stability_score,
                validation_scope=validation_scope,
            ),
        )

    @staticmethod
    def _overall_status(*results: GMVSValidationResult) -> str:
        statuses = {result.status for result in results}

        if "FAIL" in statuses:
            return "FAIL"

        if "WARN" in statuses:
            return "PASS_WITH_GAPS"

        return "PASS"

    @classmethod
    def _factory_maturity(cls, score: int, validation_scope: str) -> str:
        if validation_scope == cls.BASELINE_SCOPE:
            return "BASELINE_ESTABLISHED"

        if score >= 95:
            return "GOLD"
        if score >= 80:
            return "SILVER"
        return "BRONZE"

    @classmethod
    def _rating(cls, score: int, validation_scope: str) -> str:
        if validation_scope == cls.BASELINE_SCOPE:
            return "BASELINE"

        if score >= 95:
            return "★★★★★"
        if score >= 80:
            return "★★★★☆"
        if score >= 60:
            return "★★★☆☆"
        return "★★☆☆☆"

    @staticmethod
    def _manufacturing_status(
        manufacturing: GMVSValidationResult,
    ) -> str:
        if manufacturing.status == "PASS":
            return "Manufactured without blocking validation issues"

        if manufacturing.status == "WARN":
            return "Manufactured with validation gaps"

        return "Manufacturing validation failed"

    @classmethod
    def _build_recommendations(
        cls,
        *,
        validation_scope: str,
        architecture: GMVSValidationResult,
        readiness: GMVSValidationResult,
        manufacturing: GMVSValidationResult,
        reuse: GMVSValidationResult,
        governance: GMVSValidationResult,
    ) -> list[str]:
        recommendations: list[str] = []

        if architecture.status != "PASS":
            recommendations.append(
                "Review Factory architecture before manufacturing additional concepts."
            )

        if readiness.status != "PASS":
            recommendations.append(
                "Complete concept readiness prerequisites before production."
            )

        if manufacturing.status != "PASS":
            recommendations.append(
                "Resolve Golden Concept Package gaps before declaring the concept validated."
            )

        if reuse.status != "PASS":
            recommendations.append(
                "Review reuse findings and record any architectural evolution in FER."
            )

        if governance.status != "PASS":
            recommendations.append(
                "Complete missing governance artifacts before closing the GMVS run."
            )

        if not recommendations and validation_scope == cls.BASELINE_SCOPE:
            recommendations.append(
                "Baseline GMVS complete. Manufacture the next concept before treating "
                "reuse metrics as cross-concept evidence."
            )

        if not recommendations and validation_scope == cls.CROSS_CONCEPT_SCOPE:
            recommendations.append(
                "Cross-concept GMVS complete. Review declared reuse findings before "
                "treating them as automated code-reuse measurements."
            )

        return recommendations