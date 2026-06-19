from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from knowledge_domains.health.knowledge_manufacturing.canonical_vocabulary import CanonicalConcept, CanonicalVocabulary
from knowledge_domains.health.knowledge_manufacturing.knowledge_manufacturing_models import (
    ConceptCandidate,
    ConceptReviewItem,
    EvidenceReference,
    RecognizedConcept,
    UnknownConceptCandidate,
    stable_id,
)


class ConceptRecognitionEngine:
    """
    Department IV — Concept Recognition Engine v0.1

    Responsibility:
        Identify insurance concepts present in a certified Processed Document Asset.

    Boundary:
        This engine recognizes concepts. It does not manufacture Knowledge Atoms.
    """

    VERSION = "0.1"
    AUTO_APPROVE_THRESHOLD = 0.95
    REVIEW_THRESHOLD = 0.70

    def __init__(self, vocabulary: CanonicalVocabulary | None = None):
        self.vocabulary = vocabulary or CanonicalVocabulary()

    def recognize(self, processed_document: dict[str, Any]) -> dict[str, Any]:
        document_id = processed_document.get("document_id", "unknown_document")
        asset_id = processed_document.get("asset_id")
        source_type = ((processed_document.get("source") or {}).get("document_type") or (processed_document.get("source") or {}).get("source_type"))
        authority_score = (processed_document.get("source") or {}).get("authority_score")

        units = self._recognition_units(processed_document)
        recognized: list[RecognizedConcept] = []
        unknowns: list[UnknownConceptCandidate] = []
        review_items: list[ConceptReviewItem] = []
        seen_keys: set[str] = set()

        for unit in units:
            text = unit["text"]
            if not text or len(text.strip()) < 3:
                continue
            evidence = EvidenceReference(
                document_id=document_id,
                processed_document_asset_id=asset_id,
                section_id=unit.get("section_id"),
                clause_id=unit.get("clause_id"),
                page_number=unit.get("page_number"),
                start_line=unit.get("start_line"),
                end_line=unit.get("end_line"),
                quote=self._quote(text),
                source_document_type=source_type,
                authority_score=authority_score,
            )
            candidates = self._rank_candidates(text)
            if candidates:
                top = candidates[0]
                key = f"{unit.get('source_kind')}|{unit.get('section_id')}|{unit.get('clause_id')}|{top.canonical_id}|{self.vocabulary.normalize(text)[:80]}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                decision = self._decision(top.confidence)
                selected = top if decision in {"auto_approved", "review_required"} else None
                item = RecognizedConcept(
                    recognition_id=stable_id("rec", f"{document_id}|{asset_id}|{unit.get('source_kind')}|{text}|{top.canonical_id}"),
                    text=text[:500],
                    normalized_text=self.vocabulary.normalize(text),
                    source_kind=unit.get("source_kind", "unknown"),
                    semantic_type=top.category,
                    decision=decision,
                    selected_candidate=selected,
                    candidates=candidates[:5],
                    confidence=top.confidence,
                    evidence=evidence,
                    notes=["Concept recognized from processed document structure. No knowledge atom manufactured in Sprint 2B."],
                )
                recognized.append(item)
                if decision == "review_required":
                    review_items.append(self._review_item(item, top, reason="Confidence is below auto-approval threshold."))
            else:
                # Only create unknowns for section titles / short headings to avoid flooding the queue.
                if unit.get("source_kind") == "section" and len(text) <= 120 and self._looks_like_insurance_heading(text):
                    unknown = UnknownConceptCandidate(
                        unknown_id=stable_id("unk", f"{document_id}|{asset_id}|{text}"),
                        text=text[:300],
                        normalized_text=self.vocabulary.normalize(text),
                        reason="No canonical vocabulary match above review threshold.",
                        evidence=evidence,
                        suggested_candidates=[],
                    )
                    unknowns.append(unknown)
                    review_items.append(
                        ConceptReviewItem(
                            review_id=stable_id("crq", f"{document_id}|{asset_id}|unknown|{text}"),
                            term=text[:300],
                            normalized_term=self.vocabulary.normalize(text),
                            document_id=document_id,
                            processed_document_asset_id=asset_id,
                            suggested_canonical_id=None,
                            confidence=0.0,
                            reason="Potential new insurance concept requires human review.",
                            evidence=evidence,
                        )
                    )

        return {
            "recognized_concepts": recognized,
            "unknown_concepts": unknowns,
            "review_items": review_items,
        }

    def _recognition_units(self, processed_document: dict[str, Any]) -> list[dict[str, Any]]:
        units: list[dict[str, Any]] = []
        for section in processed_document.get("sections", []):
            title = str(section.get("title") or "").strip()
            text = str(section.get("text") or "").strip()
            loc = section.get("source_location") or {}
            if title:
                units.append({
                    "source_kind": "section",
                    "text": title,
                    "section_id": section.get("section_id"),
                    "page_number": loc.get("page_number"),
                    "start_line": loc.get("start_line"),
                    "end_line": loc.get("end_line"),
                })
            if text and len(text) > 30:
                # Use a bounded section snippet for concept recognition; atom extraction comes later.
                units.append({
                    "source_kind": "section_text",
                    "text": text[:1200],
                    "section_id": section.get("section_id"),
                    "page_number": loc.get("page_number"),
                    "start_line": loc.get("start_line"),
                    "end_line": loc.get("end_line"),
                })
        for clause in processed_document.get("clauses", [])[:2000]:
            text = str(clause.get("text") or "").strip()
            loc = clause.get("source_location") or {}
            if text:
                units.append({
                    "source_kind": "clause",
                    "text": text[:1000],
                    "clause_id": clause.get("clause_id"),
                    "page_number": loc.get("page_number"),
                    "start_line": loc.get("start_line"),
                    "end_line": loc.get("end_line"),
                })
        return units

    def _rank_candidates(self, text: str) -> list[ConceptCandidate]:
        candidates: list[ConceptCandidate] = []
        norm_text = self.vocabulary.normalize(text)
        words = set(norm_text.split())
        if not words:
            return []
        for concept in self.vocabulary.all():
            signals, matched_aliases = self._score_signals(norm_text, words, concept)
            confidence = round(
                signals["vocabulary_match"] * 0.25
                + signals["semantic_similarity"] * 0.30
                + signals["context_similarity"] * 0.20
                + signals["historical_match"] * 0.15
                + signals["rule_validation"] * 0.10,
                4,
            )
            if confidence >= self.REVIEW_THRESHOLD:
                candidates.append(
                    ConceptCandidate(
                        canonical_id=concept.canonical_id,
                        display_name=concept.display_name,
                        category=concept.category,
                        confidence=confidence,
                        signals=signals,
                        matched_aliases=matched_aliases,
                        reason=self._reason(concept, matched_aliases, signals),
                    )
                )
        candidates.sort(key=lambda item: item.confidence, reverse=True)
        return candidates

    def _score_signals(self, norm_text: str, words: set[str], concept: CanonicalConcept) -> tuple[dict[str, float], list[str]]:
        matched_aliases: list[str] = []
        alias_scores: list[float] = []
        for alias in concept.aliases:
            alias_norm = self.vocabulary.normalize(alias)
            alias_words = set(alias_norm.split())
            if not alias_words:
                continue
            if re.search(rf"\b{re.escape(alias_norm)}\b", norm_text):
                matched_aliases.append(alias)
                alias_scores.append(1.0)
            else:
                overlap = len(words & alias_words) / max(1, len(alias_words))
                if overlap >= 0.5:
                    alias_scores.append(overlap)
        vocabulary_match = max(alias_scores) if alias_scores else 0.0

        concept_words = set(self.vocabulary.normalize(" ".join([concept.display_name, concept.category, concept.description or ""])).split())
        semantic_similarity = len(words & concept_words) / max(1, len(concept_words))
        semantic_similarity = min(1.0, semantic_similarity * 2.5)

        context_words = set(self.vocabulary.normalize(" ".join(concept.context_keywords)).split())
        context_similarity = len(words & context_words) / max(1, min(len(context_words), 8)) if context_words else 0.0
        context_similarity = min(1.0, context_similarity)

        # Historical learning memory will be added after the human review loop is used.
        historical_match = 0.0
        if matched_aliases and any(alias.lower() in {"power booster", "jumpstart"} for alias in matched_aliases):
            historical_match = 0.5

        rule_validation = 0.0
        if concept.category == "waiting_period" and re.search(r"\b(day|days|month|months|year|years)\b", norm_text):
            rule_validation = 1.0
        elif concept.category in {"cost_sharing", "bonus"} and re.search(r"\b(%|percent|percentage|sum insured|claim)\b", norm_text):
            rule_validation = 1.0
        elif concept.category in {"benefit", "optional_cover", "claim_requirement", "policy_administration"} and len(words) >= 3:
            rule_validation = 0.75 if vocabulary_match > 0 else 0.25
        elif concept.category == "exclusion" and re.search(r"\b(excluded|not covered|not admissible|shall not)\b", norm_text):
            rule_validation = 1.0

        signals = {
            "vocabulary_match": round(vocabulary_match, 4),
            "semantic_similarity": round(semantic_similarity, 4),
            "context_similarity": round(context_similarity, 4),
            "historical_match": round(historical_match, 4),
            "rule_validation": round(rule_validation, 4),
        }
        return signals, matched_aliases

    def _decision(self, confidence: float) -> str:
        if confidence >= self.AUTO_APPROVE_THRESHOLD:
            return "auto_approved"
        if confidence >= self.REVIEW_THRESHOLD:
            return "review_required"
        return "unknown_concept"

    def _review_item(self, recognized: RecognizedConcept, top: ConceptCandidate, *, reason: str) -> ConceptReviewItem:
        return ConceptReviewItem(
            review_id=stable_id("crq", f"{recognized.recognition_id}|{top.canonical_id}"),
            term=recognized.text,
            normalized_term=recognized.normalized_text,
            document_id=recognized.evidence.document_id,
            processed_document_asset_id=recognized.evidence.processed_document_asset_id,
            suggested_canonical_id=top.canonical_id,
            confidence=recognized.confidence,
            reason=reason,
            evidence=recognized.evidence,
        )

    def _looks_like_insurance_heading(self, text: str) -> bool:
        keywords = {
            "cover", "benefit", "waiting", "period", "claim", "exclusion", "deductible", "premium", "policy",
            "hospital", "room", "disease", "health", "cashless", "reimbursement", "bonus", "sum insured",
        }
        low = text.lower()
        return any(keyword in low for keyword in keywords)

    def _quote(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        return text[:500]

    def _reason(self, concept: CanonicalConcept, matched_aliases: list[str], signals: dict[str, float]) -> str:
        if matched_aliases:
            return f"Matched aliases {matched_aliases[:3]} for canonical concept {concept.canonical_id}."
        return f"Matched concept {concept.canonical_id} using semantic/context signals {signals}."
