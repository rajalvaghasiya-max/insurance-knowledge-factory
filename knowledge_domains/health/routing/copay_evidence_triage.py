from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import BASE_DIR


class CopayEvidenceTriage:
    """Classify and assemble routed copay evidence without creating a product fact.

    The router intentionally favours recall. This stage adds generic precision:
    it finds local copay clauses, preserves their scope, and groups corroborating
    evidence. It never publishes a product-level copay value, default, or absence.
    """

    VERSION = "1.4"
    _COPAY_RE = re.compile(r"\bco[\s-]?pay(?:ment)?\b", re.IGNORECASE)
    _PERCENT_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?\s*%")
    _DEFINITION_RE = re.compile(r"\bmeans\b|cost[-\s]?sharing requirement|does not reduce the sum insured", re.IGNORECASE)
    _VOLUNTARY_RE = re.compile(r"\bvoluntary\b", re.IGNORECASE)
    _MANDATORY_RE = re.compile(r"\bmandatory\b", re.IGNORECASE)
    _CLAIM_MODE_RE = re.compile(r"\bpre[-\s]?approved|reimbursement\b", re.IGNORECASE)
    _GENERIC_REFERENCE_RE = re.compile(r"\bsubject to\b.*\bco[\s-]?pay(?:ment)?\b|\bco[\s-]?pay(?:ment)?\b.*\bterms\b", re.IGNORECASE | re.DOTALL)
    _DEDUCTIBLE_RE = re.compile(r"\bdeductible\b", re.IGNORECASE)
    _INTERNATIONAL_EMERGENCY_RE = re.compile(r"\binternational\s+cover\b.{0,80}\bemergency\s+care\b|\bemergency\s+care\b.{0,80}\binternational\s+cover\b", re.IGNORECASE | re.DOTALL)
    _COVER_NAME_RE = re.compile(r"\b(?P<cover>[A-Z][A-Za-z0-9&()\- /]{2,100}\bCover)\b")
    _NOT_PRE_APPROVED_RE = re.compile(r"\b(?:not|non)[-\s]?pre[-\s]?approved\b", re.IGNORECASE)
    _PRE_APPROVED_RE = re.compile(r"\bpre[-\s]?approved\b", re.IGNORECASE)
    _VOLUNTARY_DECISION_RE = re.compile(
        r"\bvoluntary\s+co[\s-]?pay(?:ment)?\b(?P<body>.{0,1400}?)"
        r"(?P<values>\d{1,3}(?:\.\d+)?\s*%(?:\s*(?:/|,|or|and)\s*\d{1,3}(?:\.\d+)?\s*%){0,8})"
        r"(?P<tail>.{0,450}?\b(?:eligible|admissible)\s+claim\s+amount\b)",
        re.IGNORECASE | re.DOTALL,
    )
    _CLAUSE_BOUNDARY_RE = re.compile(r"\n\s*(?:[a-z]\.|\d+\.|[ivxlcdm]+\.)\s*", re.IGNORECASE)
    _LOCAL_BEFORE = 100
    _LOCAL_AFTER = 180

    def triage_plan(self, routing_plan: dict[str, Any]) -> dict[str, Any]:
        if str(routing_plan.get("field")) != "copay":
            raise ValueError("CopayEvidenceTriage only accepts routing plans for field='copay'.")

        decision_bearing: list[dict[str, Any]] = []
        supporting: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        counts: dict[str, int] = {}

        for candidate in routing_plan.get("candidates", []):
            if not isinstance(candidate, dict):
                continue
            triaged = self._triage_candidate(candidate)
            counts[triaged["triage_status"]] = counts.get(triaged["triage_status"], 0) + 1
            if triaged["triage_status"] == "decision_bearing":
                decision_bearing.append(triaged)
            elif triaged["triage_status"] == "supporting_context":
                supporting.append(triaged)
            else:
                rejected.append(triaged)

        sort_key = lambda item: (-int(item.get("routing_score") or 0), str(item.get("evidence_id") or ""))
        decision_bearing.sort(key=sort_key)
        supporting.sort(key=sort_key)
        rejected.sort(key=sort_key)
        assemblies = self._assemble_clauses(decision_bearing)

        return {
            "schema_version": "1.2",
            "triage_version": self.VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entity_id": routing_plan.get("entity_id"),
            "field": "copay",
            "source_routing_plan": {
                "adapter_version": routing_plan.get("adapter_version"),
                "router_version": routing_plan.get("router_version"),
                "generated_at": routing_plan.get("generated_at"),
                "factory_dir": routing_plan.get("factory_dir"),
            },
            "input_candidate_count": len(routing_plan.get("candidates", [])),
            "status_counts": counts,
            "decision_bearing_count": len(decision_bearing),
            "supporting_context_count": len(supporting),
            "rejected_count": len(rejected),
            "decision_bearing_candidates": decision_bearing,
            "supporting_context_candidates": supporting,
            "rejected_candidates": rejected,
            "clause_assemblies": assemblies,
            "notes": [
                "This is a precision triage stage after recall-oriented evidence routing.",
                "Decision-bearing candidates require an explicit copay signal and a numeric percentage in a local copay clause.",
                "Percentages are derived from original text only, deduplicated in source order, and do not scan normalized text.",
                "Each decision fragment carries its locally evidenced condition, scope, claim mode, and coverage context where available.",
                "Clause assemblies group only context-compatible evidence; incomplete lower-authority duplicates remain corroboration, not separate product rules.",
                "No product-level copay result, default, or absence claim is created by this stage.",
            ],
        }

    def write_triage(self, triage: dict[str, Any], factory_dir: str | Path) -> Path:
        root = self._resolve_path(factory_dir)
        output_dir = root / "evidence_triage"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_entity = str(triage.get("entity_id") or "unknown").replace(":", "_").replace("/", "_").replace("\\", "_").lower()
        output_path = output_dir / f"{safe_entity}_copay_evidence_triage.json"
        output_path.write_text(json.dumps(triage, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def _triage_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        result = dict(candidate)
        text = str(candidate.get("text") or candidate.get("normalized_text") or "")
        has_copay = bool(self._COPAY_RE.search(text))
        is_definition = bool(self._DEFINITION_RE.search(text))
        is_generic_reference = bool(self._GENERIC_REFERENCE_RE.search(text))
        has_deductible = bool(self._DEDUCTIBLE_RE.search(text))
        fragments = self._decision_fragments(candidate, text)
        labels = self._ordered_unique(label for fragment in fragments for label in fragment["condition_labels"])
        percentages = self._ordered_unique(value for fragment in fragments for value in fragment["percentages"])

        if not has_copay:
            status, category = "rejected", "inherited_context_only"
            reason = "No direct copay signal exists in component text; the router match was inherited from title/context."
        elif fragments:
            status, category = "decision_bearing", "percentage_clause"
            reason = "Explicit copay signal and numeric percentage found in a locally anchored copay clause."
        elif is_definition:
            status, category = "supporting_context", "definition"
            reason = "Generic copay definition retained as supporting context; it is not a product-specific copay outcome."
        elif is_generic_reference:
            status, category = "supporting_context", "generic_reference"
            reason = "Generic copay reference retained as context; no amount or product condition is stated."
        else:
            status, category = "supporting_context", "context_reference"
            reason = "Copay is mentioned but the clause contains no locally anchored numeric percentage or decision-bearing condition."

        result.update({
            "triage_status": status,
            "triage_category": category,
            "triage_reason": reason,
            "decision_fragments": fragments,
            "triage_signals": {
                "direct_copay_in_text": has_copay,
                "percentages": percentages,
                "voluntary": "voluntary" in labels,
                "mandatory": "mandatory" in labels,
                "claim_mode_specific": "claim_mode_specific" in labels,
                "definition": is_definition,
                "generic_reference": is_generic_reference,
                "deductible_present": has_deductible,
            },
            "condition_labels": labels,
        })
        return result

    def _decision_fragments(self, candidate: dict[str, Any], text: str) -> list[dict[str, Any]]:
        fragments: list[dict[str, Any]] = []

        # A voluntary copay clause can span a title, discount explanation, and an
        # application sentence. Use the semantic claim-amount anchor, rather than
        # a small fixed window, so the policy-wording clause is not lost.
        for match in self._VOLUNTARY_DECISION_RE.finditer(text):
            start, end = match.start(), match.end()
            clause = text[start:end].strip()
            values = self._ordered_unique(self._PERCENT_RE.findall(match.group("values")))
            if values:
                fragments.append(self._fragment(candidate, "voluntary", start, end, clause, values, ["voluntary"], text))

        # Mandatory clauses are read forward from their own marker. Their scope
        # can appear either as a nearby label or elsewhere in the same component.
        for match in self._MANDATORY_RE.finditer(text):
            start = match.start()
            end = self._sentence_end(text, match.end(), self._LOCAL_AFTER)
            clause = text[start:end].strip()
            values = self._ordered_unique(self._PERCENT_RE.findall(clause))
            if values and self._COPAY_RE.search(clause):
                fragments.append(self._fragment(candidate, "mandatory", start, end, clause, values, ["mandatory"], text))

        # Claim-mode clauses can begin before the literal copay phrase ("20%
        # co-payment") and must retain that exact mode rather than infer a default.
        for match in self._COPAY_RE.finditer(text):
            start = max(0, match.start() - self._LOCAL_BEFORE)
            end = self._sentence_end(text, match.end(), self._LOCAL_AFTER)
            clause = text[start:end].strip()
            values = self._ordered_unique(self._PERCENT_RE.findall(clause))
            if not values:
                continue
            labels: list[str] = []
            if self._CLAIM_MODE_RE.search(clause):
                labels.append("claim_mode_specific")
            if labels:
                fragments.append(self._fragment(candidate, match.group(0), start, end, clause, values, labels, text))

        return self._unique_fragments(fragments)

    def _fragment(
        self,
        candidate: dict[str, Any],
        anchor: str,
        start: int,
        end: int,
        text: str,
        percentages: list[str],
        labels: list[str],
        full_text: str,
    ) -> dict[str, Any]:
        scope = self._scope_context(text, full_text, start, end, labels)
        coverage_context = self._coverage_context(candidate, text, full_text, start, labels)
        return {
            "fragment_id": self._fragment_id(str(candidate.get("evidence_id") or "unknown"), start, end),
            "anchor": anchor,
            "text": text,
            "percentages": percentages,
            "condition_labels": labels,
            "scope_context": scope,
            "coverage_context": coverage_context,
            "source_char_range": {"start": start, "end": end},
        }

    def _scope_context(self, clause: str, full_text: str, start: int, end: int, labels: list[str]) -> dict[str, Any]:
        context = full_text[max(0, start - 280): min(len(full_text), end + 320)]
        scope_labels: list[str] = []
        scope_text: list[str] = []

        international = self._INTERNATIONAL_EMERGENCY_RE.search(context) or self._INTERNATIONAL_EMERGENCY_RE.search(full_text)
        if international and "mandatory" in labels:
            scope_labels.append("international_emergency_care_only")
            scope_text.append(self._compact(international.group(0)))

        if "claim_mode_specific" in labels:
            mode_match = re.search(r".{0,65}\b(?:pre[-\s]?approved|reimbursement)\b.{0,100}", clause, re.IGNORECASE | re.DOTALL)
            if mode_match:
                scope_labels.append("claim_mode_specific")
                scope_text.append(self._compact(mode_match.group(0)))

        if "voluntary" in labels:
            scope_labels.append("voluntary_option")
            scope_text.append("voluntary co-payment option")

        return {
            "scope_labels": self._ordered_unique(scope_labels),
            "scope_text": self._ordered_unique(scope_text),
            "scope_status": "explicit" if scope_labels else "not_explicit_in_local_clause",
        }

    def _coverage_context(
        self,
        candidate: dict[str, Any],
        clause: str,
        full_text: str,
        start: int,
        labels: list[str],
    ) -> dict[str, Any]:
        """Capture named cover and claim-mode distinctions without inferring a default."""
        prefix = full_text[:start]
        cover_match = None
        for match in self._COVER_NAME_RE.finditer(prefix):
            cover_match = match
        if cover_match is None:
            # A short component can begin with its coverage heading, placing it
            # inside the local clause rather than before the copay anchor.
            for match in self._COVER_NAME_RE.finditer(clause):
                cover_match = match
                break
        if cover_match is None:
            for key in ("title_hint", "parent_title_hint"):
                hinted = str(candidate.get(key) or "")
                match = self._COVER_NAME_RE.search(hinted)
                if match:
                    cover_match = match
                    break
        coverage_labels: list[str] = []
        coverage_text: list[str] = []
        if cover_match:
            cover = self._compact(cover_match.group("cover"))
            coverage_text.append(cover)
            coverage_labels.append(re.sub(r"[^a-z0-9]+", "_", cover).strip("_"))

        claim_mode = None
        search_surface = f"{clause} {prefix[-240:]}"
        if "claim_mode_specific" in labels:
            if self._NOT_PRE_APPROVED_RE.search(search_surface):
                claim_mode = "not_pre_approved_reimbursement"
            elif self._PRE_APPROVED_RE.search(search_surface):
                claim_mode = "pre_approved_reimbursement"
            elif re.search(r"\breimbursement\b", search_surface, re.IGNORECASE):
                claim_mode = "reimbursement_unspecified"

        return {
            "coverage_labels": self._ordered_unique(coverage_labels),
            "coverage_text": self._ordered_unique(coverage_text),
            "claim_mode": claim_mode,
            "context_status": "explicit" if coverage_labels or claim_mode else "not_explicit_in_local_context",
        }

    def _assemble_clauses(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for candidate in candidates:
            for fragment in candidate.get("decision_fragments", []):
                if not isinstance(fragment, dict):
                    continue
                key = self._assembly_key(fragment)
                groups.setdefault(key, []).append(self._assembly_member(candidate, fragment))

        assemblies: list[dict[str, Any]] = []
        unscoped_groups: list[tuple[str, list[dict[str, Any]]]] = []
        for key, members in groups.items():
            if self._is_unscoped_assembly_key(key):
                unscoped_groups.append((key, members))
                continue
            assemblies.append(self._build_assembly(key, members))

        # A lower-authority clause that repeats the same local wording but omits
        # scope is corroboration only. It cannot create a second, broader rule.
        for key, members in unscoped_groups:
            attached = False
            for member in members:
                target = self._find_scoped_duplicate_target(member, assemblies)
                if target is not None:
                    enriched = dict(member)
                    enriched["corroboration_role"] = "scope_incomplete_lower_authority_duplicate"
                    target["corroborating_evidence"].append(enriched)
                    target["evidence_count"] += 1
                    attached = True
            if not attached:
                assemblies.append(self._build_assembly(key, members))

        assemblies = self._merge_scope_coverage_hierarchy(assemblies)
        for assembly in assemblies:
            assembly["corroborating_evidence"].sort(
                key=lambda item: (-int(item.get("authority_score") or 0), -int(item.get("routing_score") or 0), str(item.get("evidence_id") or ""))
            )
        return sorted(assemblies, key=lambda item: (-int(item["primary_evidence"].get("authority_score") or 0), item["assembly_id"]))

    def _assembly_member(self, candidate: dict[str, Any], fragment: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": candidate.get("evidence_id"),
            "classified_component_id": candidate.get("classified_component_id"),
            "document_id": candidate.get("document_id"),
            "document_type": candidate.get("document_type") or candidate.get("source_type"),
            "authority_score": candidate.get("authority_score"),
            "routing_score": candidate.get("routing_score"),
            "fragment_id": fragment.get("fragment_id"),
            "source_char_range": fragment.get("source_char_range"),
            "fragment_text": fragment.get("text"),
            "canonical_fragment_text": self._canonical_clause_text(str(fragment.get("text") or "")),
            "coverage_context": fragment.get("coverage_context") or {},
        }

    def _build_assembly(self, key: str, members: list[dict[str, Any]]) -> dict[str, Any]:
        members = sorted(members, key=lambda item: (-int(item.get("authority_score") or 0), -int(item.get("routing_score") or 0), str(item.get("evidence_id") or "")))
        primary = members[0]
        parts = key.split("|")
        return {
            "assembly_id": f"cpa_{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}",
            "assembly_key": key,
            "percentages": parts[0].split(",") if parts[0] else [],
            "condition_labels": parts[1].split(",") if parts[1] else [],
            "scope_labels": parts[2].split(",") if parts[2] else [],
            "coverage_labels": parts[3].split(",") if parts[3] else [],
            "claim_mode": parts[4] or None,
            "primary_evidence": primary,
            "corroborating_evidence": members[1:],
            "evidence_count": len(members),
            "status": "evidence_assembled_not_fact_extracted",
        }

    def _merge_scope_coverage_hierarchy(self, assemblies: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge a broader lower-authority coverage label into a specific scope rule.

        This is deliberately narrow. It applies only where a scope itself supplies a
        more specific coverage meaning, for example ``international_emergency_care_only``
        versus the broader ``international_cover`` label. Original fragment context is
        retained unchanged; the assembly records the normalized relationship.
        """
        retained: list[dict[str, Any]] = []
        for assembly in sorted(
            assemblies,
            key=lambda item: (-int((item.get("primary_evidence") or {}).get("authority_score") or 0), item.get("assembly_id") or ""),
        ):
            target = self._find_scope_coverage_hierarchy_target(assembly, retained)
            if target is None:
                self._apply_scope_coverage_normalization(assembly)
                retained.append(assembly)
                continue

            # The lower-authority assembly is not a separate rule. Preserve its
            # primary evidence as corroboration, without changing its local context.
            member = dict(assembly.get("primary_evidence") or {})
            member["corroboration_role"] = "broader_coverage_context_lower_authority_duplicate"
            target["corroborating_evidence"].append(member)
            target["corroborating_evidence"].extend(assembly.get("corroborating_evidence") or [])
            target["evidence_count"] = int(target.get("evidence_count") or 0) + int(assembly.get("evidence_count") or 0)
            self._apply_scope_coverage_normalization(target)
        return retained

    def _find_scope_coverage_hierarchy_target(
        self,
        candidate: dict[str, Any],
        retained: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        candidate_primary = candidate.get("primary_evidence") or {}
        candidate_authority = int(candidate_primary.get("authority_score") or 0)
        candidate_scope = set(candidate.get("scope_labels") or [])
        candidate_coverage = set(candidate.get("coverage_labels") or [])
        if candidate_scope != {"international_emergency_care_only"} or candidate_coverage != {"international_cover"}:
            return None

        for target in retained:
            target_primary = target.get("primary_evidence") or {}
            target_authority = int(target_primary.get("authority_score") or 0)
            if candidate_authority >= target_authority:
                continue
            if target.get("percentages") != candidate.get("percentages"):
                continue
            if target.get("condition_labels") != candidate.get("condition_labels"):
                continue
            if target.get("scope_labels") != candidate.get("scope_labels"):
                continue
            if target.get("claim_mode") != candidate.get("claim_mode"):
                continue
            target_coverage = set(target.get("coverage_labels") or [])
            if not target_coverage or target_coverage == {"international_emergency_care"}:
                return target
        return None

    @staticmethod
    def _apply_scope_coverage_normalization(assembly: dict[str, Any]) -> None:
        scope_labels = set(assembly.get("scope_labels") or [])
        if "international_emergency_care_only" not in scope_labels:
            return
        labels = list(assembly.get("coverage_labels") or [])
        if "international_emergency_care" not in labels:
            labels.append("international_emergency_care")
        assembly["coverage_labels"] = labels
        assembly["coverage_context_normalization"] = {
            "status": "normalized_from_explicit_scope",
            "normalized_coverage_label": "international_emergency_care",
            "basis_scope_label": "international_emergency_care_only",
        }

    @staticmethod
    def _is_unscoped_assembly_key(key: str) -> bool:
        parts = key.split("|")
        return len(parts) >= 5 and not parts[2] and not parts[3] and not parts[4]

    @staticmethod
    def _canonical_clause_text(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", text.lower())

    def _find_scoped_duplicate_target(self, member: dict[str, Any], assemblies: list[dict[str, Any]]) -> dict[str, Any] | None:
        source_text = str(member.get("canonical_fragment_text") or "")
        source_authority = int(member.get("authority_score") or 0)
        for assembly in assemblies:
            primary = assembly.get("primary_evidence") or {}
            scoped = bool(assembly.get("scope_labels") or assembly.get("coverage_labels") or assembly.get("claim_mode"))
            if not scoped:
                continue
            primary_text = str(primary.get("canonical_fragment_text") or "")
            if source_text and source_text == primary_text and source_authority < int(primary.get("authority_score") or 0):
                return assembly
        return None

    @staticmethod
    def _assembly_key(fragment: dict[str, Any]) -> str:
        values = ",".join(fragment.get("percentages") or [])
        labels = ",".join(fragment.get("condition_labels") or [])
        scope = ",".join((fragment.get("scope_context") or {}).get("scope_labels") or [])
        coverage = fragment.get("coverage_context") or {}
        coverage_labels = ",".join(coverage.get("coverage_labels") or [])
        claim_mode = str(coverage.get("claim_mode") or "")
        return f"{values}|{labels}|{scope}|{coverage_labels}|{claim_mode}"

    @staticmethod
    def _sentence_end(text: str, position: int, maximum: int) -> int:
        window_end = min(len(text), position + maximum)
        terminator = re.search(r"[.!?]", text[position:window_end])
        return position + terminator.end() if terminator else window_end

    @staticmethod
    def _unique_fragments(fragments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []
        seen: set[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = set()
        for fragment in fragments:
            scope = tuple((fragment.get("scope_context") or {}).get("scope_labels") or [])
            signature = (tuple(fragment["percentages"]), tuple(fragment["condition_labels"]), scope)
            if signature in seen:
                continue
            seen.add(signature)
            unique.append(fragment)
        return unique

    @staticmethod
    def _fragment_id(evidence_id: str, start: int, end: int) -> str:
        digest = hashlib.sha256(f"{evidence_id}|{start}|{end}".encode("utf-8")).hexdigest()[:16]
        return f"cpf_{digest}"

    @staticmethod
    def _compact(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    @staticmethod
    def _ordered_unique(values: Any) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()
        for value in values:
            value = str(value)
            if value not in seen:
                seen.add(value)
                output.append(value)
        return output

    @staticmethod
    def _resolve_path(path: str | Path) -> Path:
        candidate = Path(path)
        return candidate if candidate.is_absolute() else BASE_DIR / candidate
