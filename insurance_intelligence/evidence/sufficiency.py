from __future__ import annotations
def evaluate(requirement_results):
    if not requirement_results:return 'MISSING','NO_REQUIREMENTS'
    statuses={r.status for r in requirement_results}
    if 'FAILED_LINEAGE' in statuses:return 'FAILED_LINEAGE','NOT_RESOLVED'
    if 'ENTITY_UNRESOLVED' in statuses:return 'ENTITY_UNRESOLVED','NOT_RESOLVED'
    if 'VERSION_UNRESOLVED' in statuses:return 'VERSION_UNRESOLVED','NOT_RESOLVED'
    if 'CONFLICTING' in statuses:return 'CONFLICTING','CONFLICTING'
    if statuses=={'SATISFIED'}:return 'COMPLETE','RESOLVED'
    if statuses<={'SATISFIED','SATISFIED_WITH_LIMITATIONS'}:return 'SUFFICIENT','RESOLVED_WITH_LIMITATIONS'
    if 'PARTIALLY_SATISFIED' in statuses:return 'PARTIAL','PARTIALLY_RESOLVED'
    return 'MISSING','NOT_RESOLVED'
