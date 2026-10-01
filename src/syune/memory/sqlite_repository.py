"""Local durable reference adapter. JSON and schema are private storage details."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from syune.core import (
    AssociationId, ClaimId, ConceptId, Confidence, EpisodeId, EvidenceId,
    MemoryTraceId, ObservationId, ProcedureId, ProvenanceId, SourceId,
    SourceVersionId,
)
from .model import (
    Association, Claim, Concept, ContradictionKind, Episode, Evidence, EvidencePolarity,
    MemoryTrace, NodeId, Observation, Procedure, Provenance, Source,
    SourceLocator, TruthMetadata, TruthState,
)
from .security import DefaultAccessPolicy, SecurityEnvelope, Sensitivity
from .lifecycle import LifecycleMetrics, LifecycleRecord, LifecycleState, MemoryClass
from .repository import (
    DuplicateIdError, InMemoryReferenceRepository, MemoryObject,
    MissingEndpointError,
    _truth_events,
)

SCHEMA_VERSION = 1
_TYPES = {cls.__name__: cls for cls in (
    AssociationId, ClaimId, ConceptId, EpisodeId, EvidenceId, MemoryTraceId,
    ObservationId, ProcedureId, ProvenanceId, SourceId, SourceVersionId,
    Confidence, SourceLocator, Provenance, TruthMetadata, SecurityEnvelope, LifecycleRecord, Source, Observation, Concept,
    Claim, Evidence, Episode, Procedure, MemoryTrace, Association,
)}
_ENUMS = {item.__name__: item for item in (EvidencePolarity, TruthState, ContradictionKind, Sensitivity, DefaultAccessPolicy, LifecycleState, MemoryClass)}
_ENTITIES = (Source, Observation, Concept, Claim, Evidence, Episode, Procedure, MemoryTrace)


def _encode(value: object) -> object:
    if isinstance(value, datetime):
        return {"datetime": value.isoformat()}
    if isinstance(value, Enum):
        return {"enum": type(value).__name__, "value": value.value}
    if isinstance(value, tuple):
        return {"tuple": [_encode(item) for item in value]}
    if is_dataclass(value):
        return {"type": type(value).__name__, "fields": {
            item.name: _encode(getattr(value, item.name)) for item in fields(value)
        }}
    if value is None or type(value) in (str, int, float, bool):
        return value
    # UUID is the sole non-dataclass primitive inside typed IDs.
    from uuid import UUID
    if isinstance(value, UUID):
        return {"uuid": str(value)}
    raise TypeError(f"unsupported persistence value: {type(value).__name__}")


def _decode(value: object) -> object:
    if isinstance(value, list):
        raise ValueError("unexpected list in memory storage")
    if not isinstance(value, dict):
        return value
    if "uuid" in value:
        from uuid import UUID
        return UUID(value["uuid"])
    if "datetime" in value:
        return datetime.fromisoformat(value["datetime"])
    if "tuple" in value:
        return tuple(_decode(item) for item in value["tuple"])
    if "enum" in value:
        return _ENUMS[value["enum"]](value["value"])
    cls = _TYPES[value["type"]]
    return cls(**{name: _decode(item) for name, item in value["fields"].items()})


def _key(entity_id: object) -> tuple[str, str]:
    return type(entity_id).__name__, str(entity_id)


class SQLiteMemoryRepository:
    """Single-process SQLite reference store satisfying MemoryRepository."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.execute("PRAGMA foreign_keys = ON")
        try:
            with self._db:
                self._db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                row = self._db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
                if row is None:
                    # A database without a version is only acceptable when no memory tables exist.
                    existing = {r[0] for r in self._db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if existing - {"metadata"}:
                        raise ValueError("unversioned memory schema")
                    self._db.execute("INSERT INTO metadata VALUES ('schema_version',?)", (str(SCHEMA_VERSION),))
                elif row[0] != str(SCHEMA_VERSION):
                    raise ValueError(f"incompatible memory schema version: {row[0]}")
                if row is not None:
                    tables={r[0] for r in self._db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if not {"metadata","entities","associations"}.issubset(tables): raise ValueError("incomplete memory schema")
                self._db.execute("""CREATE TABLE IF NOT EXISTS entities (
                    id_type TEXT NOT NULL, id_value TEXT NOT NULL, entity_type TEXT NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY (id_type,id_value))""")
                self._db.execute("""CREATE TABLE IF NOT EXISTS associations (
                    id_value TEXT PRIMARY KEY, source_type TEXT NOT NULL, source_value TEXT NOT NULL,
                    target_type TEXT NOT NULL, target_value TEXT NOT NULL, payload TEXT NOT NULL)""")
                self._db.execute("CREATE INDEX IF NOT EXISTS associations_source ON associations(source_type,source_value)")
                self._db.execute("CREATE INDEX IF NOT EXISTS associations_target ON associations(target_type,target_value)")
                self._db.execute("""CREATE TABLE IF NOT EXISTS change_journal (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, operation TEXT NOT NULL,
                    id_type TEXT NOT NULL, id_value TEXT NOT NULL)""")
                self._db.execute("""CREATE TABLE IF NOT EXISTS lifecycle (
                    id_type TEXT NOT NULL, id_value TEXT NOT NULL, state TEXT NOT NULL,
                    fingerprint TEXT, payload TEXT NOT NULL, PRIMARY KEY(id_type,id_value))""")
                self._db.execute("CREATE INDEX IF NOT EXISTS lifecycle_state ON lifecycle(state)")
                self._db.execute("CREATE INDEX IF NOT EXISTS lifecycle_fingerprint ON lifecycle(fingerprint,state)")
                self._db.execute("""CREATE TABLE IF NOT EXISTS lifecycle_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
                    id_type TEXT NOT NULL, id_value TEXT NOT NULL, occurred_at TEXT NOT NULL,
                    from_state TEXT, to_state TEXT NOT NULL, reason TEXT NOT NULL)""")
        except Exception:
            self._db.close()
            raise

    def __enter__(self) -> "SQLiteMemoryRepository":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    def _exists(self, entity_id: NodeId) -> bool:
        return self._db.execute("SELECT 1 FROM entities WHERE id_type=? AND id_value=?", _key(entity_id)).fetchone() is not None

    def put(self, entity: MemoryObject) -> None:
        self.put_many((entity,))

    def put_many(self, entities: tuple[MemoryObject, ...]) -> None:
        if not isinstance(entities, tuple):
            raise TypeError("entities must be a tuple")
        with self._db:
            for entity in entities:
                if not isinstance(entity, _ENTITIES):
                    raise TypeError("unsupported memory entity")
                if self._exists(entity.id):
                    raise DuplicateIdError(f"duplicate entity ID: {entity.id}")
                if isinstance(entity, Evidence) and any(not self._exists(cid) for cid in entity.claim_ids):
                    raise MissingEndpointError("evidence claim IDs must exist")
                if isinstance(entity, MemoryTrace) and not self._exists(entity.entity_id):
                    raise MissingEndpointError("trace target must exist")
                payload = json.dumps(_encode(entity), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                self._db.execute("INSERT INTO entities VALUES (?,?,?,?)", (*_key(entity.id), type(entity).__name__, payload))
                self._db.execute("INSERT INTO change_journal(operation,id_type,id_value) VALUES ('INSERT',?,?)", _key(entity.id))
                record=LifecycleRecord(entity.id,created_at=getattr(entity,"created_at",None) or getattr(entity,"registered_at"),
                    memory_class=MemoryClass.ORGANIZATIONAL if isinstance(entity,Source) else MemoryClass.SEMANTIC,
                    protected=isinstance(entity,Source))
                self._db.execute("INSERT INTO lifecycle VALUES (?,?,?,?,?)", (*_key(entity.id),record.state.value,None,json.dumps(_encode(record),sort_keys=True,separators=(",",":"))))

    def replace(self, entity: MemoryObject, operation: str = "UPDATE") -> None:
        if not isinstance(entity, _ENTITIES) or not self._exists(entity.id): raise KeyError(entity.id)
        payload = json.dumps(_encode(entity), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._db:
            self._db.execute("UPDATE entities SET entity_type=?,payload=? WHERE id_type=? AND id_value=?",
                             (type(entity).__name__, payload, *_key(entity.id)))
            self._db.execute("INSERT INTO change_journal(operation,id_type,id_value) VALUES (?,?,?)",
                             (operation, *_key(entity.id)))

    def get(self, entity_id: NodeId) -> MemoryObject | None:
        InMemoryReferenceRepository._require_node_id(entity_id)
        row = self._db.execute("SELECT payload FROM entities WHERE id_type=? AND id_value=?", _key(entity_id)).fetchone()
        if row is None: return None
        entity = _decode(json.loads(row[0]))
        if not isinstance(entity, _ENTITIES) or entity.id != entity_id:
            raise ValueError("memory row identity mismatch")
        return entity

    def exists(self, entity_id: NodeId) -> bool:
        InMemoryReferenceRepository._require_node_id(entity_id)
        return self._exists(entity_id)

    def get_many(self, entity_ids: tuple[NodeId, ...]) -> tuple[MemoryObject, ...]:
        return tuple(item for item in (self.get(entity_id) for entity_id in entity_ids) if item is not None)

    def entity_count(self) -> int:
        return int(self._db.execute("SELECT COUNT(*) FROM entities").fetchone()[0])

    def changes_since(self, cursor: int, limit: int = 1024):
        rows = tuple(self._db.execute("SELECT sequence,id_type,id_value FROM change_journal WHERE sequence>? ORDER BY sequence LIMIT ?", (cursor, limit)))
        if not rows: return cursor, ()
        from syune.core import ClaimId, ConceptId, EpisodeId, EvidenceId, MemoryTraceId, ObservationId, ProcedureId, SourceId
        kinds = {item.__name__: item for item in (SourceId,ObservationId,ConceptId,ClaimId,EvidenceId,EpisodeId,ProcedureId,MemoryTraceId)}
        ids = tuple(kinds[kind].parse(value) for _,kind,value in rows)
        return rows[-1][0], self.get_many(ids)

    def add_association(self, association: Association) -> None:
        if not isinstance(association, Association):
            raise TypeError("expected Association")
        with self._db:
            if self.get_association(association.id) is not None:
                raise DuplicateIdError(f"duplicate association ID: {association.id}")
            if not self._exists(association.source_id) or not self._exists(association.target_id):
                raise MissingEndpointError("both association endpoints must exist")
            payload = json.dumps(_encode(association), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            self._db.execute("INSERT INTO associations VALUES (?,?,?,?,?,?)", (
                str(association.id), *_key(association.source_id), *_key(association.target_id), payload,
            ))

    def get_association(self, association_id: AssociationId) -> Association | None:
        if not isinstance(association_id, AssociationId):
            raise TypeError("expected AssociationId")
        row = self._db.execute("SELECT id_value,source_type,source_value,target_type,target_value,payload FROM associations WHERE id_value=?", (str(association_id),)).fetchone()
        return self._association_row(row) if row else None

    @staticmethod
    def _association_row(row):
        edge = _decode(json.loads(row[5]))
        if not isinstance(edge,Association) or (str(edge.id),*_key(edge.source_id),*_key(edge.target_id))!=tuple(row[:5]):
            raise ValueError("association row identity mismatch")
        return edge

    def associations_for(self, entity_id: NodeId) -> tuple[Association, ...]:
        InMemoryReferenceRepository._require_node_id(entity_id)
        kind, value = _key(entity_id)
        rows = self._db.execute("""SELECT id_value,source_type,source_value,target_type,target_value,payload FROM associations WHERE
            (source_type=? AND source_value=?) OR (target_type=? AND target_value=?) ORDER BY rowid""",
            (kind, value, kind, value))
        return tuple(self._association_row(row) for row in rows)

    def iter_entities(self) -> tuple[MemoryObject, ...]:
        rows = self._db.execute("SELECT id_type,id_value,entity_type,payload FROM entities ORDER BY id_type,id_value")
        entities = []
        for kind,value,entity_type,payload in rows:
            item = _decode(json.loads(payload))
            if not isinstance(item,_ENTITIES) or _key(item.id)!=(kind,value) or type(item).__name__!=entity_type:
                raise ValueError("memory row identity mismatch")
            entities.append(item)
        return tuple(entities)

    def truth_events(self):
        return _truth_events(self.iter_entities())

    def lifecycle(self, entity_id):
        InMemoryReferenceRepository._require_node_id(entity_id)
        row=self._db.execute("SELECT payload FROM lifecycle WHERE id_type=? AND id_value=?",_key(entity_id)).fetchone()
        if row is None: return LifecycleRecord(entity_id)
        value=_decode(json.loads(row[0]))
        if not isinstance(value,LifecycleRecord): raise ValueError("invalid lifecycle row")
        return value

    def set_lifecycle(self, record):
        if not isinstance(record,LifecycleRecord): raise TypeError("LifecycleRecord required")
        prior=self.lifecycle(record.entity_id) if self._exists(record.entity_id) or self._db.execute("SELECT 1 FROM lifecycle WHERE id_type=? AND id_value=?",_key(record.entity_id)).fetchone() else None
        payload=json.dumps(_encode(record),sort_keys=True,separators=(",",":"))
        if prior is not None and prior.state is record.state:
            kind="memory_reinforced" if record.reinforcement_count>prior.reinforcement_count else "memory_lifecycle_updated"
        else:
            kind={LifecycleState.ACTIVE:"memory_restored",LifecycleState.ARCHIVED:"memory_archived",LifecycleState.FORGOTTEN:"memory_forgotten",LifecycleState.PURGED:"memory_purged"}[record.state]
        with self._db:
            self._db.execute("""INSERT INTO lifecycle(id_type,id_value,state,fingerprint,payload) VALUES (?,?,?,?,?)
                ON CONFLICT(id_type,id_value) DO UPDATE SET state=excluded.state,
                fingerprint=excluded.fingerprint,payload=excluded.payload""",
                (*_key(record.entity_id),record.state.value,record.content_fingerprint,payload))
            self._db.execute("INSERT INTO lifecycle_events(kind,id_type,id_value,occurred_at,from_state,to_state,reason) VALUES (?,?,?,?,?,?,?)",
                (kind,*_key(record.entity_id),record.changed_at.isoformat(),prior.state.value if prior else None,record.state.value,record.reason))
            if record.source_memory_ids and (prior is None or record.source_memory_ids!=prior.source_memory_ids):
                self._db.execute("INSERT INTO lifecycle_events(kind,id_type,id_value,occurred_at,from_state,to_state,reason) VALUES (?,?,?,?,?,?,?)",
                    ("memory_consolidated",*_key(record.entity_id),record.changed_at.isoformat(),prior.state.value if prior else None,record.state.value,"exact duplicate lineage recorded"))
            self._db.execute("INSERT INTO change_journal(operation,id_type,id_value) VALUES ('LIFECYCLE',?,?)",_key(record.entity_id))

    def transition_lifecycle(self,entity_id,state,reason):
        from dataclasses import replace
        from syune.core import utc_now
        current=self.lifecycle(entity_id)
        if current.state is LifecycleState.PURGED: raise ValueError("purged memory cannot transition")
        if current.state is LifecycleState.FORGOTTEN and state is LifecycleState.ACTIVE: raise ValueError("forgotten memory requires administrative recovery policy")
        self.set_lifecycle(replace(current,state=state,changed_at=utc_now(),reason=reason))

    def reinforce(self,entity_id,reason):
        from dataclasses import replace
        from syune.core import utc_now
        current=self.lifecycle(entity_id)
        self.set_lifecycle(replace(current,last_reinforced_at=utc_now(),reinforcement_count=current.reinforcement_count+1,reason=reason))

    def record_access(self,entity_id):
        from dataclasses import replace
        current=self.lifecycle(entity_id); updated=replace(current,access_count=current.access_count+1)
        payload=json.dumps(_encode(updated),sort_keys=True,separators=(",",":"))
        with self._db: self._db.execute("UPDATE lifecycle SET payload=? WHERE id_type=? AND id_value=?",(payload,*_key(entity_id)))

    def find_active_fingerprint(self,fingerprint):
        row=self._db.execute("SELECT id_type,id_value FROM lifecycle WHERE fingerprint=? AND state='ACTIVE' ORDER BY id_type,id_value LIMIT 1",(fingerprint,)).fetchone()
        if not row: return None
        kinds={item.__name__:item for item in (SourceId,ObservationId,ConceptId,ClaimId,EvidenceId,EpisodeId,ProcedureId,MemoryTraceId)}
        return kinds[row[0]].parse(row[1])

    def lifecycle_scan(self,cursor,limit):
        rows=tuple(self._db.execute("SELECT payload FROM lifecycle ORDER BY rowid LIMIT ? OFFSET ?",(limit,cursor)))
        return cursor+len(rows),tuple(_decode(json.loads(row[0])) for row in rows)

    def lifecycle_changes_since(self,cursor,limit=1024):
        rows=tuple(self._db.execute("SELECT sequence,id_type,id_value FROM change_journal WHERE sequence>? AND operation='LIFECYCLE' ORDER BY sequence LIMIT ?",(cursor,limit)))
        if not rows:return cursor,()
        kinds={item.__name__:item for item in (SourceId,ObservationId,ConceptId,ClaimId,EvidenceId,EpisodeId,ProcedureId,MemoryTraceId)}
        return rows[-1][0],tuple((kinds[k].parse(v),self.lifecycle(kinds[k].parse(v)).state) for _,k,v in rows)

    def purge(self,entity_id,reason):
        from dataclasses import replace
        from syune.core import utc_now
        self.set_lifecycle(replace(self.lifecycle(entity_id),state=LifecycleState.PURGED,changed_at=utc_now(),reason=reason,content_fingerprint=None))
        with self._db:
            kind,value=_key(entity_id)
            self._db.execute("DELETE FROM associations WHERE (source_type=? AND source_value=?) OR (target_type=? AND target_value=?)",(kind,value,kind,value))
            self._db.execute("DELETE FROM entities WHERE id_type=? AND id_value=?",(kind,value))

    def lifecycle_events(self):
        return tuple(self._db.execute("SELECT sequence,kind,id_type,id_value,occurred_at,from_state,to_state,reason FROM lifecycle_events ORDER BY sequence"))

    def lifecycle_metrics(self):
        counts={state:0 for state in LifecycleState}
        for state,count in self._db.execute("SELECT state,COUNT(*) FROM lifecycle GROUP BY state"): counts[LifecycleState(state)]=count
        consolidated=int(self._db.execute("SELECT COUNT(*) FROM lifecycle WHERE payload NOT LIKE '%\"source_memory_ids\":{\"tuple\":[]}%' ").fetchone()[0])
        return LifecycleMetrics(counts[LifecycleState.ACTIVE],counts[LifecycleState.ARCHIVED],counts[LifecycleState.FORGOTTEN],counts[LifecycleState.PURGED],consolidated,0,0.0)
