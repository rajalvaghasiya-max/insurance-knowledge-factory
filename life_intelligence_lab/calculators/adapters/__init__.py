"""
life_intelligence_lab.calculators.adapters
=============================================

Contained wrappers around third-party numerical dependencies. No caller,
CLI request, agent, or explanation anywhere in this codebase is permitted
to invoke a third-party library's API directly -- every call passes
through an adapter here, which is the only place the dependency's exact
identity, version, and behavior are known. See `pyxirr_adapter.py` and
CALCULATOR_ARCHITECTURE.md for why.
"""
