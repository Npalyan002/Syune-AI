"""Durable, sanitized execution evidence and exactly-one semantic commits."""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .model import AttemptEvidence, BudgetLimit, ModelExecutionResult

_SECRET_KEYS = frozenset({"authorization", "api_key", "apikey", "credential", "secret",
                          "session", "cookie", "set-cookie", "proxy-authorization"})


def sanitize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return sanitize(asdict(value))
    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items()
                if str(k).casefold() not in _SECRET_KEYS}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((sanitize(item) for item in value), key=lambda item: json.dumps(item,sort_keys=True,default=str))
    if isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            pass
        else:
            return json.dumps(sanitize(decoded), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return value


def canonical(value: Any) -> str:
    return json.dumps(sanitize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      default=lambda item: item.value if hasattr(item, "value") else str(item))


class EvidenceStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS attempts(
                    provider_attempt_id TEXT PRIMARY KEY,
                    logical_call_id TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    provider TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    state TEXT NOT NULL DEFAULT '',
                    timestamp TEXT NOT NULL DEFAULT '',
                    evidence_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS commits(
                    logical_call_id TEXT PRIMARY KEY,
                    semantic_commit_id TEXT NOT NULL UNIQUE,
                    request_fingerprint TEXT NOT NULL,
                    result_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transitions(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    logical_call_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    detail_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS budget_reservations(
                    reservation_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    calls REAL NOT NULL,
                    input_tokens REAL NOT NULL,
                    output_tokens REAL NOT NULL,
                    cost_usd REAL NOT NULL,
                    reconciled INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(reservation_id,scope,scope_id)
                );
            """)
        attempt_columns = {row[1] for row in self.db.execute("PRAGMA table_info(attempts)")}
        for name in ("provider", "model", "state", "timestamp"):
            if name not in attempt_columns:
                with self.db: self.db.execute(f"ALTER TABLE attempts ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(commits)")}
        if "request_fingerprint" not in columns:
            with self.db:
                self.db.execute("ALTER TABLE commits ADD COLUMN request_fingerprint TEXT NOT NULL DEFAULT ''")
        with self.db:
            self.db.executescript("""
                CREATE INDEX IF NOT EXISTS idx_attempts_logical ON attempts(logical_call_id,attempt_number);
                CREATE INDEX IF NOT EXISTS idx_attempts_provider_model ON attempts(provider,model);
                CREATE INDEX IF NOT EXISTS idx_attempts_state_time ON attempts(state,timestamp);
                CREATE INDEX IF NOT EXISTS idx_commits_fingerprint ON commits(request_fingerprint);
                CREATE INDEX IF NOT EXISTS idx_transitions_logical ON transitions(logical_call_id,sequence);
                CREATE INDEX IF NOT EXISTS idx_budget_scope ON budget_reservations(scope,scope_id);
            """)

    def transition(self, logical_call_id: str, state: str, detail: dict[str, Any] | None = None) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT INTO transitions(logical_call_id,state,detail_json) VALUES(?,?,?)",
                            (logical_call_id, state, canonical(detail or {})))

    def reserve_budget(self, reservation_id: str, limits: tuple[BudgetLimit, ...], *,
                       input_tokens: int, output_tokens: int, cost: float) -> None:
        with self._lock, self.db:
            for limit in limits:
                row = self.db.execute("SELECT COALESCE(SUM(calls),0),COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0),COALESCE(SUM(cost_usd),0) FROM budget_reservations WHERE scope=? AND scope_id=?",
                    (limit.scope,limit.scope_id)).fetchone()
                projected=(row[0]+1,row[1]+input_tokens,row[2]+output_tokens,row[3]+cost)
                caps=(limit.max_calls,limit.max_input_tokens,limit.max_output_tokens,limit.max_cost_usd)
                if any(cap is not None and value>cap for cap,value in zip(caps,projected)):
                    raise RuntimeError("BUDGET_EXCEEDED")
            for limit in limits:
                self.db.execute("INSERT INTO budget_reservations VALUES(?,?,?,?,?,?,?,0)",
                    (reservation_id,limit.scope,limit.scope_id,1,input_tokens,output_tokens,cost))

    def reconcile_budget(self, reservation_id: str, *, input_tokens: int | None,
                         output_tokens: int | None, cost: float | None) -> None:
        if input_tokens is None or output_tokens is None or cost is None: return
        with self._lock, self.db:
            self.db.execute("UPDATE budget_reservations SET input_tokens=?,output_tokens=?,cost_usd=?,reconciled=1 WHERE reservation_id=?",
                            (input_tokens,output_tokens,cost,reservation_id))

    def recover_incomplete(self, logical_call_id: str) -> str | None:
        with self._lock:
            row=self.db.execute("SELECT state,detail_json FROM transitions WHERE logical_call_id=? ORDER BY sequence DESC LIMIT 1",(logical_call_id,)).fetchone()
        if row and row[0] == "BUDGET_RESERVED":
            attempt=json.loads(row[1]).get("attempt")
            if attempt:
                with self._lock,self.db: self.db.execute("DELETE FROM budget_reservations WHERE reservation_id=? AND reconciled=0",(attempt,))
            self.transition(logical_call_id,"RESERVATION_RELEASED",{"attempt":attempt,"recovered_after_process_restart":True})
            return "RESERVATION_RELEASED"
        if row and row[0] in {"REQUEST_STARTED","HTTP_RESPONSE_RECEIVED"}:
            self.transition(logical_call_id,"REMOTE_COMPLETION_AMBIGUOUS",{"recovered_after_process_restart":True})
            return "REMOTE_COMPLETION_AMBIGUOUS"
        return None

    def persist_attempt(self, evidence: AttemptEvidence) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO attempts(provider_attempt_id,logical_call_id,attempt_number,provider,model,state,timestamp,evidence_json) VALUES(?,?,?,?,?,?,?,?)",
                            (evidence.provider_attempt_id, evidence.logical_call_id,
                             evidence.attempt_number, evidence.provider, evidence.requested_model,
                             evidence.state.value, evidence.timestamp, canonical(asdict(evidence))))

    def commit(self, result: ModelExecutionResult, request_fingerprint: str) -> bool:
        if result.semantic_commit_id is None:
            raise ValueError("commit requires semantic_commit_id")
        with self._lock, self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO commits(logical_call_id,semantic_commit_id,request_fingerprint,result_json) VALUES(?,?,?,?)",
                (result.logical_call_id, result.semantic_commit_id, request_fingerprint, canonical(asdict(result))))
            return cursor.rowcount == 1

    def committed(self, logical_call_id: str, request_fingerprint: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            row = self.db.execute("SELECT request_fingerprint,result_json FROM commits WHERE logical_call_id=?",
                                  (logical_call_id,)).fetchone()
        if not row: return None
        if request_fingerprint is not None and row[0] != request_fingerprint:
            raise ValueError("IDEMPOTENCY_CONFLICT")
        return json.loads(row[1])

    def evidence(self, logical_call_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [json.loads(row[0]) for row in self.db.execute(
                "SELECT evidence_json FROM attempts WHERE logical_call_id=? ORDER BY attempt_number",
                (logical_call_id,))]

    def transitions(self, logical_call_id: str) -> list[str]:
        with self._lock:
            return [row[0] for row in self.db.execute(
                "SELECT state FROM transitions WHERE logical_call_id=? ORDER BY sequence", (logical_call_id,))]

    def close(self) -> None:
        self.db.close()
