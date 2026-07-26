"""
life_intelligence_lab
======================

Experimental, sandboxed prototype code for PolicyScna's future Life
Intelligence data layer.

STATUS: PROTOTYPE / RESEARCH ONLY. NOT PRODUCTION CODE.

This package is intentionally isolated from PolicyScna's active Health
implementation (`factory_core/`, `insurance_intelligence/`, production
contracts and orchestrators). It has its own dependency declarations and
its own test suite, and must never be imported by production code.

Scope of this prototype: AMFI mutual-fund NAV data only. No insurer ULIP
data, no calculators, no fund comparison, no recommendations, no LLM, no
database, no orchestration framework.
"""

__all__ = []

PROTOTYPE_VERSION = "0.1.0"
