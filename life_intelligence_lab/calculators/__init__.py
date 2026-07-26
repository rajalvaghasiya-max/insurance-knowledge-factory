"""
life_intelligence_lab.calculators
==================================

EXPERIMENTAL / PROTOTYPE. NOT PRODUCTION CODE.

Isolated deterministic Time Value of Money (TVM) calculator runtime.
Implements only: Future Value, Present Value, CAGR, and Inflation-Adjusted
Future Value (exact and a separately-named approximate method).

Does NOT depend on anything AMFI-specific from the sibling
LIFE-PROTOTYPE-001 adapter code (`life_intelligence_lab.downloader`,
`.parser`, `.contracts` at the package root, `.canonical` at the package
root). This subpackage has its own contracts, its own canonical
serialization, and its own registry -- see ARCHITECTURE.md for why.

No LLM, no financial recommendations, no tax logic, no market-data
fetching, no product comparison, no ULIP/HLV/surrender logic, and no
database or orchestration framework are present anywhere in this
subpackage.
"""

PROTOTYPE_STATUS = "EXPERIMENTAL"

__all__ = []
