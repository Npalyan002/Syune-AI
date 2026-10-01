from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

_SECRET_KEYS = frozenset({"authorization", "api_key", "apikey", "credential", "secret",
                          "cookie", "set-cookie", "proxy-authorization", "token"})


def _safe(value: Any) -> Any:
    if isinstance(value, Enum): return value.value
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _safe(item) for key, item in value.items()
                if str(key).casefold() not in _SECRET_KEYS}
    if isinstance(value, (tuple, list, set, frozenset)): return [_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)): return value
    return str(value)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    sequence: int
    operation_id: str
    timestamp: str
    operation_type: str
    outcome: str
    correlation_id: str | None
    principal: dict[str, Any]
    purpose: str | None
    scopes: dict[str, Any]
    authorization_decisions: tuple[str, ...]
    resource_ids: tuple[str, ...]
    context_ids: tuple[str, ...]
    lifecycle_action: str | None
    logical_call_id: str | None
    detail: dict[str, Any]


class SQLiteAuditStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path; self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS audit_events(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    correlation_id TEXT,
                    principal_json TEXT NOT NULL,
                    purpose TEXT,
                    scopes_json TEXT NOT NULL,
                    authorization_json TEXT NOT NULL,
                    resource_ids_json TEXT NOT NULL,
                    context_ids_json TEXT NOT NULL,
                    lifecycle_action TEXT,
                    logical_call_id TEXT,
                    detail_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit_operation ON audit_events(operation_id,sequence);
                CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id,sequence);
                CREATE INDEX IF NOT EXISTS idx_audit_logical_call ON audit_events(logical_call_id,sequence);
            """)

    def record(self, *, operation_id: str, operation_type: str, outcome: str,
               correlation_id: str | None = None, principal: Mapping[str, Any] | None = None,
               purpose: str | None = None, scopes: Mapping[str, Any] | None = None,
               authorization_decisions: tuple[str, ...] = (), resource_ids: tuple[str, ...] = (),
               context_ids: tuple[str, ...] = (), lifecycle_action: str | None = None,
               logical_call_id: str | None = None, detail: Mapping[str, Any] | None = None) -> int:
        if not operation_id.strip() or not operation_type.strip() or not outcome.strip():
            raise ValueError("operation_id, operation_type, and outcome are required")
        values = (operation_id, datetime.now(timezone.utc).isoformat(), operation_type, outcome,
                  correlation_id, json.dumps(_safe(principal or {}), sort_keys=True), purpose,
                  json.dumps(_safe(scopes or {}), sort_keys=True),
                  json.dumps(_safe(authorization_decisions)), json.dumps(_safe(resource_ids)),
                  json.dumps(_safe(context_ids)), lifecycle_action, logical_call_id,
                  json.dumps(_safe(detail or {}), sort_keys=True))
        with self.db:
            cursor = self.db.execute("INSERT INTO audit_events(operation_id,timestamp,operation_type,outcome,correlation_id,principal_json,purpose,scopes_json,authorization_json,resource_ids_json,context_ids_json,lifecycle_action,logical_call_id,detail_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        return int(cursor.lastrowid)

    def query(self, *, limit: int = 100, operation_id: str | None = None,
              correlation_id: str | None = None, logical_call_id: str | None = None) -> tuple[AuditEvent, ...]:
        if not 1 <= limit <= 1000: raise ValueError("limit must be 1..1000")
        where, args = [], []
        for column, value in (("operation_id", operation_id), ("correlation_id", correlation_id),
                              ("logical_call_id", logical_call_id)):
            if value is not None: where.append(f"{column}=?"); args.append(value)
        sql = "SELECT * FROM audit_events" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY sequence DESC LIMIT ?"
        args.append(limit)
        rows = self.db.execute(sql, args).fetchall()
        return tuple(AuditEvent(row["sequence"], row["operation_id"], row["timestamp"],
            row["operation_type"], row["outcome"], row["correlation_id"], json.loads(row["principal_json"]),
            row["purpose"], json.loads(row["scopes_json"]), tuple(json.loads(row["authorization_json"])),
            tuple(json.loads(row["resource_ids_json"])), tuple(json.loads(row["context_ids_json"])),
            row["lifecycle_action"], row["logical_call_id"], json.loads(row["detail_json"])) for row in rows)

    def close(self) -> None: self.db.close()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
