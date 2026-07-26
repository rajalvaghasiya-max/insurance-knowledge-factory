from __future__ import annotations
from dataclasses import dataclass,field
from insurance_intelligence.contracts.evidence import TraceEvent
@dataclass
class TraceBuilder:
    trace_id:str
    _events:list[TraceEvent]=field(default_factory=list)
    def add(self,event_type,decision,basis,*,requirement_id=None,subject_reference=None,repository=None,candidate_reference=None,source_paths=()):
        seq=len(self._events)+1
        self._events.append(TraceEvent(self.trace_id,seq,event_type,requirement_id,subject_reference,repository,candidate_reference,decision,basis,tuple(source_paths),f"event-{seq:04d}"))
    def build(self): return tuple(self._events)
