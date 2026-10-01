from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json

from syune.audit import SQLiteAuditStore
from syune.memory import MemoryRepository
from syune.retrieval import RecallRequest, RetrievalService


class ProvenanceMode(str, Enum):
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    FULL = "FULL"


@dataclass(frozen=True, slots=True)
class ContextItem:
    typed_entity_id: str
    entity_type: str
    content: str
    source_id: str | None
    score: float
    truth_state: str | None
    temporally_valid: bool
    provenance_valid: bool
    provenance: dict[str, object]
    audit_sequence: int | None


@dataclass(frozen=True, slots=True)
class ContextAssembly:
    request_id: str
    rendered: str
    items: tuple[ContextItem, ...]
    truncated: bool
    score_meaning: str = "retrieval relevance, not truth probability"


class ContextService:
    """Converts governed retrieval into a bounded model-ready payload."""
    def __init__(self, memory: MemoryRepository, retrieval: RetrievalService,
                 audit: SQLiteAuditStore | None = None):
        self.memory, self.retrieval = memory, retrieval
        self.audit_store = audit
        self.audit_events: list[dict[str, object]] = []

    @staticmethod
    def _content(entity: object) -> str:
        for name in ("content", "statement", "label", "summary", "description", "display_name"):
            value = getattr(entity, name, None)
            if isinstance(value, str) and value.strip(): return value.strip()
        steps = getattr(entity, "steps", None)
        return "\n".join(steps) if steps else type(entity).__name__

    def _provenance(self, entity: object, mode: ProvenanceMode) -> dict[str, object]:
        provenance = getattr(entity, "provenance", None)
        source_id = getattr(provenance, "source_id", None)
        source = self.memory.get(source_id) if source_id is not None else None
        truth = getattr(entity, "truth", None)
        security = getattr(entity, "security", None)
        base: dict[str, object] = {
            "memory_id": f"{type(entity.id).__name__}:{entity.id}",
            "source_id": f"SourceId:{source_id}" if source_id else None,
            "origin": ({"kind": getattr(source, "kind", None),
                        "display_name": getattr(source, "display_name", None)} if source else None),
            "observed_at": getattr(entity, "observed_at", None),
            "recorded_at": getattr(truth, "recorded_at", None) if truth else None,
            "valid_from": getattr(truth, "valid_from", None) if truth else None,
            "valid_until": getattr(truth, "valid_until", None) if truth else None,
            "revision_of": (f"{type(truth.revision_of).__name__}:{truth.revision_of}"
                            if truth and truth.revision_of else None),
            "supersedes": ([f"{type(item).__name__}:{item}" for item in truth.supersedes]
                           if truth else []),
            "supersession_state": getattr(getattr(truth, "state", None), "value", None),
            "scope": ({"owner": getattr(security, "owner", None),
                       "organization": getattr(security, "organization_scope", None),
                       "project": getattr(security, "project_scope", None),
                       "department": getattr(security, "department_scope", None),
                       "agent": getattr(security, "agent_scope", None),
                       "purposes": list(getattr(security, "purpose_constraints", ()))} if security else None),
        }
        if mode is ProvenanceMode.MINIMAL:
            return {key: base[key] for key in ("memory_id", "source_id", "supersession_state")}
        if mode is ProvenanceMode.FULL:
            base["lineage"] = {
                "provenance_id": f"ProvenanceId:{provenance.id}" if provenance else None,
                "parent_provenance_ids": ([f"ProvenanceId:{item}" for item in provenance.parent_provenance_ids]
                                          if provenance else []),
                "process_id": getattr(provenance, "process_id", None),
                "pipeline_version": getattr(provenance, "pipeline_version", None),
                "locator": repr(getattr(provenance, "locator", None)) if provenance and provenance.locator else None,
            }
        return base

    def assemble(self, request: RecallRequest, *, max_chars: int = 8_000,
                 provenance_mode: ProvenanceMode | str = ProvenanceMode.STANDARD) -> ContextAssembly:
        if type(max_chars) is not int or not 256 <= max_chars <= 100_000:
            raise ValueError("max_chars must be 256..100000")
        selected_mode = provenance_mode if isinstance(provenance_mode, ProvenanceMode) else ProvenanceMode(provenance_mode)
        access_start = len(self.retrieval.access_events)
        recalled = self.retrieval.recall(request)
        raw_items, sections, used, clipped = [], [], 0, False
        for candidate in recalled.candidates:
            entity = self.memory.get(candidate.entity_id)
            if entity is None: continue
            content = self._content(entity)
            provenance = self._provenance(entity, selected_mode)
            line = (f"[{type(candidate.entity_id).__name__}:{candidate.entity_id}] {content}\n"
                    f"[provenance {json.dumps(provenance, default=str, separators=(',', ':'))}]")
            if used + len(line) + 1 > max_chars:
                clipped = True; break
            used += len(line) + 1; sections.append(line)
            raw_items.append((candidate, entity, content, provenance))
        operation_id = request.cue.correlation_id or str(recalled.request_id)
        access_events = self.retrieval.access_events[access_start:]
        audit_sequence = None
        if self.audit_store is not None:
            access = request.cue.access_context
            principal = access.principal if access else None
            audit_sequence = self.audit_store.record(operation_id=operation_id, correlation_id=request.cue.correlation_id,
                operation_type="context", outcome="SUCCESS" if raw_items else "EMPTY",
                principal={name: getattr(principal, name) for name in ("user_id", "agent_id", "service_id") if principal and getattr(principal, name)},
                purpose=access.purpose if access else None,
                scopes={name: getattr(principal, name) for name in ("organization_id", "project_id", "department_id") if principal and getattr(principal, name)},
                authorization_decisions=tuple(event.decision.value for event in access_events),
                resource_ids=tuple(str(event.resource_id) for event in access_events),
                context_ids=tuple(f"{type(candidate.entity_id).__name__}:{candidate.entity_id}" for candidate,_,_,_ in raw_items),
                detail={"query_mode": request.cue.query_mode.value, "provenance_mode": selected_mode.value,
                        "truncated": clipped or bool(recalled.truncated)})
        items = tuple(ContextItem(f"{type(candidate.entity_id).__name__}:{candidate.entity_id}",
                candidate.entity_type, content, f"SourceId:{candidate.source_id}" if candidate.source_id else None,
                candidate.score, candidate.truth_state.value if candidate.truth_state else None,
                candidate.temporally_valid, candidate.provenance_valid,
                provenance, audit_sequence)
            for candidate, entity, content, provenance in raw_items)
        assembly = ContextAssembly(str(recalled.request_id), "\n".join(sections), items,
                                   clipped or bool(recalled.truncated))
        self.audit_events.append({"at": datetime.now(timezone.utc).isoformat(), "operation": "context",
                                  "request_id": assembly.request_id, "items": len(items),
                                  "truncated": assembly.truncated})
        if len(self.audit_events) > 1024: del self.audit_events[:-1024]
        return assembly

    def audit(self, limit: int = 100) -> tuple[dict[str, object], ...]:
        if not 1 <= limit <= 1000: raise ValueError("limit must be 1..1000")
        return tuple(self.audit_events[-limit:])
