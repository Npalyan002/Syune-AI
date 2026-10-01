"""Single-database durable ledger, overlay, consolidation, and rollback audit."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Protocol

from syune.core import (
    AssociationId, ClaimId, ConceptId, ConsolidationBatchId, EpisodeId, EvidenceId,
    LearningProposalId, LearningSignalId, MemoryTraceId, ObservationId, ProcedureId,
    ProvenanceId, SourceId,
)
from .errors import LearningError, LearningErrorCode
from .model import (
    ConsolidationBatch, FeedbackLabel, LearningProposal, LearningSignal,
    LearningSignalKind, LearningSource, LearningStatus, LearningTarget,
    PlasticityState, TargetKind,
)

DB_SCHEMA_VERSION = "1"
_IDS = {cls.__name__: cls for cls in (SourceId, ObservationId, ConceptId, ClaimId, EvidenceId,
        EpisodeId, ProcedureId, MemoryTraceId, AssociationId)}


class LearningLedger(Protocol):
    def append(self, signal: LearningSignal) -> bool: ...
    def get(self, signal_id: LearningSignalId) -> LearningSignal | None: ...
    def pending(self, limit: int) -> tuple[LearningSignal, ...]: ...
    def by_target(self, target_key: str) -> tuple[LearningSignal, ...]: ...
    def by_correlation(self, correlation_id: str) -> tuple[LearningSignal, ...]: ...
    def count_signals(self) -> int: ...


class PlasticityOverlay(Protocol):
    def state(self, target_key: str) -> PlasticityState: ...
    def snapshot(self) -> tuple[PlasticityState, ...]: ...


def _target(raw: str) -> LearningTarget:
    kind, value = raw.split(":", 1)
    return LearningTarget(_IDS[kind].parse(value))


def _signal_json(signal: LearningSignal) -> str:
    return json.dumps({
        "id": str(signal.id), "kind": signal.kind.value, "occurred_at": signal.occurred_at.isoformat(),
        "targets": [x.key for x in signal.targets], "source": signal.source.value,
        "idempotency_key": signal.idempotency_key, "provenance_id": str(signal.provenance_id),
        "correlation_id": signal.correlation_id,
        "context_ids": [f"{type(x).__name__}:{x}" for x in signal.context_ids],
        "outcome_value": signal.outcome_value,
        "feedback_label": signal.feedback_label.value if signal.feedback_label else None,
        "schema_version": signal.schema_version,
    }, sort_keys=True, separators=(",", ":"))


def _signal(raw: str) -> LearningSignal:
    value = json.loads(raw)
    return LearningSignal(
        LearningSignalId.parse(value["id"]), LearningSignalKind(value["kind"]),
        datetime.fromisoformat(value["occurred_at"]), tuple(_target(x) for x in value["targets"]),
        LearningSource(value["source"]), value["idempotency_key"], ProvenanceId.parse(value["provenance_id"]),
        value["correlation_id"], tuple(_target(x).id for x in value["context_ids"]), value["outcome_value"],
        FeedbackLabel(value["feedback_label"]) if value["feedback_label"] else None, value["schema_version"])


def _state(row) -> PlasticityState:
    if row is None:
        raise ValueError("state row required")
    return PlasticityState(row[0], TargetKind(row[1]), row[2], row[3], row[4], bool(row[5]), row[6],
                           datetime.fromisoformat(row[7]) if row[7] else None, row[8])


class SQLiteLearningStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        try:
            self._initialize()
        except Exception:
            self._db.close()
            raise

    def _initialize(self) -> None:
        tables = self._db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if tables:
            row = self._db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if row is None or row[0] != DB_SCHEMA_VERSION:
                raise LearningError(LearningErrorCode.INCOMPATIBLE_SCHEMA, "learning schema mismatch")
            return
        self._db.executescript("""
        CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        INSERT INTO metadata VALUES('schema_version','1');
        CREATE TABLE signals(id TEXT PRIMARY KEY,idempotency_key TEXT UNIQUE NOT NULL,payload TEXT NOT NULL,
          kind TEXT NOT NULL,occurred_at TEXT NOT NULL,correlation_id TEXT,processed_batch_id TEXT);
        CREATE TABLE signal_targets(signal_id TEXT NOT NULL,target_key TEXT NOT NULL,
          PRIMARY KEY(signal_id,target_key),FOREIGN KEY(signal_id) REFERENCES signals(id));
        CREATE TABLE overlay(target_key TEXT PRIMARY KEY,target_kind TEXT NOT NULL,utility REAL NOT NULL,
          salience REAL NOT NULL,association REAL NOT NULL,retraction INTEGER NOT NULL,update_count INTEGER NOT NULL,
          updated_at TEXT,schema_version TEXT NOT NULL);
        CREATE TABLE batches(id TEXT PRIMARY KEY,payload TEXT NOT NULL,status TEXT NOT NULL);
        CREATE TABLE proposals(id TEXT PRIMARY KEY,batch_id TEXT NOT NULL,signal_id TEXT NOT NULL,target_key TEXT NOT NULL,
          before_json TEXT NOT NULL,after_json TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL);
        CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,ref_id TEXT NOT NULL,
          occurred_at TEXT NOT NULL,payload TEXT NOT NULL);
        """)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def append(self, signal: LearningSignal) -> bool:
        existing = self._db.execute("SELECT id FROM signals WHERE idempotency_key=?", (signal.idempotency_key,)).fetchone()
        if existing:
            return existing[0] == str(signal.id)
        try:
            with self._db:
                self._db.execute("INSERT INTO signals VALUES(?,?,?,?,?,?,NULL)",
                    (str(signal.id), signal.idempotency_key, _signal_json(signal), signal.kind.value,
                     signal.occurred_at.isoformat(), signal.correlation_id))
                self._db.executemany("INSERT INTO signal_targets VALUES(?,?)",
                    ((str(signal.id), target.key) for target in signal.targets))
                self._db.execute("INSERT INTO audit(event_type,ref_id,occurred_at,payload) VALUES(?,?,?,?)",
                    ("learning.signal_recorded", str(signal.id), signal.occurred_at.isoformat(), _signal_json(signal)))
        except sqlite3.IntegrityError as exc:
            raise LearningError(LearningErrorCode.DUPLICATE_SIGNAL, "duplicate signal identity") from exc
        return True

    def get(self, signal_id: LearningSignalId) -> LearningSignal | None:
        row = self._db.execute("SELECT payload FROM signals WHERE id=?", (str(signal_id),)).fetchone()
        return _signal(row[0]) if row else None

    def pending(self, limit: int) -> tuple[LearningSignal, ...]:
        rows = self._db.execute("SELECT payload FROM signals WHERE processed_batch_id IS NULL ORDER BY occurred_at,id LIMIT ?", (limit,)).fetchall()
        return tuple(_signal(row[0]) for row in rows)

    def by_target(self, target_key: str) -> tuple[LearningSignal, ...]:
        rows = self._db.execute("SELECT s.payload FROM signals s JOIN signal_targets t ON t.signal_id=s.id WHERE t.target_key=? ORDER BY s.occurred_at,s.id", (target_key,)).fetchall()
        return tuple(_signal(row[0]) for row in rows)

    def by_correlation(self, correlation_id: str) -> tuple[LearningSignal, ...]:
        rows = self._db.execute("SELECT payload FROM signals WHERE correlation_id=? ORDER BY occurred_at,id", (correlation_id,)).fetchall()
        return tuple(_signal(row[0]) for row in rows)

    def count_signals(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

    def state(self, target_key: str) -> PlasticityState:
        row = self._db.execute("SELECT target_key,target_kind,utility,salience,association,retraction,update_count,updated_at,schema_version FROM overlay WHERE target_key=?", (target_key,)).fetchone()
        return _state(row) if row else PlasticityState(target_key, TargetKind.ENTITY)

    def snapshot(self) -> tuple[PlasticityState, ...]:
        rows = self._db.execute("SELECT target_key,target_kind,utility,salience,association,retraction,update_count,updated_at,schema_version FROM overlay ORDER BY target_key").fetchall()
        return tuple(_state(row) for row in rows)

    @staticmethod
    def _state_json(state: PlasticityState) -> str:
        value = asdict(state)
        value["target_kind"] = state.target_kind.value
        value["updated_at"] = state.updated_at.isoformat() if state.updated_at else None
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _state_from_json(raw: str) -> PlasticityState:
        value = json.loads(raw)
        value["target_kind"] = TargetKind(value["target_kind"])
        value["updated_at"] = datetime.fromisoformat(value["updated_at"]) if value["updated_at"] else None
        return PlasticityState(**value)

    def apply_batch(self, batch: ConsolidationBatch, proposals: tuple[LearningProposal, ...]) -> None:
        try:
            self._db.execute("BEGIN IMMEDIATE")
            for signal_id in batch.signal_ids:
                row = self._db.execute("SELECT processed_batch_id FROM signals WHERE id=?", (str(signal_id),)).fetchone()
                if row is None or row[0] is not None:
                    raise LearningError(LearningErrorCode.CONSOLIDATION_FAILED, "signal unavailable or already processed")
            batch_payload = json.dumps({"signal_ids": [str(x) for x in batch.signal_ids],
                "proposal_ids": [str(x) for x in batch.proposal_ids], "checksum": batch.checksum,
                "total_ms": batch.total_ms, "policy_version": batch.policy_version}, sort_keys=True)
            self._db.execute("INSERT INTO batches VALUES(?,?,?)", (str(batch.id), batch_payload, batch.status.value))
            for item in proposals:
                after = item.after
                self._db.execute("INSERT OR REPLACE INTO overlay VALUES(?,?,?,?,?,?,?,?,?)",
                    (after.target_key, after.target_kind.value, after.utility_delta, after.salience_delta,
                     after.association_delta, int(after.retraction_flag), after.update_count,
                     after.updated_at.isoformat() if after.updated_at else None, after.schema_version))
                payload = json.dumps({"reason": item.reason, "policy_version": item.policy_version,
                                      "created_at": item.created_at.isoformat()}, sort_keys=True)
                self._db.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?)",
                    (str(item.id), str(batch.id), str(item.signal_id), item.target_key,
                     self._state_json(item.before), self._state_json(item.after), payload, LearningStatus.APPLIED.value))
            self._db.executemany("UPDATE signals SET processed_batch_id=? WHERE id=?",
                                 ((str(batch.id), str(x)) for x in batch.signal_ids))
            self._db.execute("INSERT INTO audit(event_type,ref_id,occurred_at,payload) VALUES(?,?,?,?)",
                ("consolidation.completed", str(batch.id), batch.completed_at.isoformat(), batch_payload))
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def rollback(self, batch_id: ConsolidationBatchId, at: datetime) -> tuple[PlasticityState, ...]:
        row = self._db.execute("SELECT status FROM batches WHERE id=?", (str(batch_id),)).fetchone()
        if row is None: raise LearningError(LearningErrorCode.ROLLBACK_NOT_FOUND, "batch not found")
        if row[0] == LearningStatus.ROLLED_BACK.value:
            raise LearningError(LearningErrorCode.ALREADY_ROLLED_BACK, "batch already rolled back")
        rows = self._db.execute("SELECT target_key,before_json FROM proposals WHERE batch_id=? ORDER BY rowid", (str(batch_id),)).fetchall()
        earliest = {}
        for key, before in rows: earliest.setdefault(key, self._state_from_json(before))
        last = self._db.execute("SELECT MAX(rowid) FROM proposals WHERE batch_id=?", (str(batch_id),)).fetchone()[0]
        for key in earliest:
            later = self._db.execute("SELECT 1 FROM proposals WHERE target_key=? AND rowid>? AND status=? LIMIT 1", (key,last,LearningStatus.APPLIED.value)).fetchone()
            if later:
                raise LearningError(LearningErrorCode.CONSOLIDATION_FAILED,"rollback would overwrite a later applied update")
        with self._db:
            for state in earliest.values():
                if state.update_count == 0:
                    self._db.execute("DELETE FROM overlay WHERE target_key=?", (state.target_key,))
                else:
                    self._db.execute("INSERT OR REPLACE INTO overlay VALUES(?,?,?,?,?,?,?,?,?)",
                        (state.target_key, state.target_kind.value, state.utility_delta, state.salience_delta,
                         state.association_delta, int(state.retraction_flag), state.update_count,
                         state.updated_at.isoformat() if state.updated_at else None, state.schema_version))
            self._db.execute("UPDATE proposals SET status=? WHERE batch_id=?", (LearningStatus.ROLLED_BACK.value, str(batch_id)))
            self._db.execute("UPDATE batches SET status=? WHERE id=?", (LearningStatus.ROLLED_BACK.value, str(batch_id)))
            self._db.execute("INSERT INTO audit(event_type,ref_id,occurred_at,payload) VALUES(?,?,?,?)",
                             ("learning.rollback_applied", str(batch_id), at.isoformat(), "{}"))
        return tuple(earliest.values())

    def audit(self, ref_id: str | None = None) -> tuple[tuple[str, str, str], ...]:
        if ref_id:
            rows = self._db.execute("SELECT event_type,ref_id,payload FROM audit WHERE ref_id=? ORDER BY seq", (ref_id,)).fetchall()
        else:
            rows = self._db.execute("SELECT event_type,ref_id,payload FROM audit ORDER BY seq").fetchall()
        return tuple(rows)

    def proposal_audit(self, target_key: str) -> tuple[tuple[str, str, str, str], ...]:
        """Trace overlay target -> proposal -> signal -> batch without hiding provenance IDs."""
        rows = self._db.execute(
            "SELECT id,signal_id,batch_id,status FROM proposals WHERE target_key=? ORDER BY rowid",
            (target_key,)).fetchall()
        return tuple(rows)
