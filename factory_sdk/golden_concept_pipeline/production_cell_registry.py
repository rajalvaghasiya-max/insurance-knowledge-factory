from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Protocol

from .execution_models import ManufacturingContext, ProductionResult


class ProductionCell(Protocol):
    cell_name: str

    def run(self, context: ManufacturingContext) -> ProductionResult:
        ...


@dataclass(frozen=True)
class CellRegistration:
    asset_type: str
    production_cell_name: str
    status: str
    version: str


class ProductionCellRegistry:
    """Runtime registry for executable production cells.

    GCMP asks the registry for a cell.  It never imports or branches on a
    department directly.
    """

    def __init__(self) -> None:
        self._cells: Dict[str, ProductionCell] = {}
        self._registrations: Dict[str, CellRegistration] = {}

    def register(self, asset_type: str, cell: ProductionCell, *, version: str = "1.0", status: str = "available") -> None:
        self._cells[asset_type] = cell
        self._registrations[asset_type] = CellRegistration(
            asset_type=asset_type,
            production_cell_name=cell.cell_name,
            status=status,
            version=version,
        )

    def get(self, asset_type: str) -> ProductionCell | None:
        return self._cells.get(asset_type)

    def is_available(self, asset_type: str) -> bool:
        return asset_type in self._cells

    def to_dict(self) -> Dict[str, object]:
        return {
            "registered_cells": {
                key: {
                    "asset_type": value.asset_type,
                    "production_cell": value.production_cell_name,
                    "status": value.status,
                    "version": value.version,
                }
                for key, value in sorted(self._registrations.items())
            }
        }
