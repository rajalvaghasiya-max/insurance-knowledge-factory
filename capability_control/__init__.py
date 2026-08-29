"""PolicyScna capability-control plane.

The control plane is repository governance, not insurance-domain runtime.  It
keeps a small semantic catalog and continuously reconciles those claims against
derivable repository structure.
"""

from .catalog import (
    CapabilityCatalog,
    CapabilityCatalogError,
    CapabilityRecord,
    load_catalog,
    validate_catalog,
)
from .scanner import CapabilityDriftReport, scan_repository

__all__ = [
    "CapabilityCatalog",
    "CapabilityCatalogError",
    "CapabilityDriftReport",
    "CapabilityRecord",
    "load_catalog",
    "scan_repository",
    "validate_catalog",
]
