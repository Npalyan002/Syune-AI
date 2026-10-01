"""Exactly-once cognitive application of committed ModelGateway results.

The mutator receives the ledger's SQLite connection so its writes and the APPLIED
marker share one database transaction. Cross-database effects must use an existing
idempotent domain API and are not falsely advertised as atomic here.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

from .model import ExecutionState, ModelExecutionRequest, ModelExecutionResult
from .persistence import canonical
from .runtime import ModelGateway


class CognitiveTransactionState(str, Enum):
    NOT_APPLIED = "NOT_APPLIED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CognitiveOperation:
    operation_key: str
    subsystem: str
    principal: str
    purpose: str
    authorized_context_ids: tuple[str, ...]
    request: ModelExecutionRequest

    def __post_init__(self) -> None:
        if not all((self.operation_key.strip(), self.subsystem.strip(), self.principal.strip(), self.purpose.strip())):
            raise ValueError("cognitive operation identity, subsystem, principal, and purpose are required")
        if self.request.principal != self.principal or self.request.purpose != self.purpose:
            raise ValueError("authorized operation identity must match the gateway request")


@dataclass(frozen=True)
class CognitiveTransactionResult:
    cognitive_transaction_id: str
    gateway_logical_call_id: str
    gateway_semantic_commit_id: str
    state: CognitiveTransactionState
    value: Any
    replayed: bool


def cognitive_transaction_id(operation: CognitiveOperation, result: ModelExecutionResult) -> str:
    if not result.semantic_commit_id:
        raise ValueError("committed gateway result required")
    body = canonical({"operation_key": operation.operation_key,
                      "logical_call_id": result.logical_call_id,
                      "semantic_commit_id": result.semantic_commit_id})
    return hashlib.sha256(body.encode()).hexdigest()


class CognitiveTransactionLedger:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path; self._lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=30000;
            CREATE TABLE IF NOT EXISTS cognitive_transactions(
                cognitive_transaction_id TEXT PRIMARY KEY,
                operation_key TEXT NOT NULL,
                subsystem TEXT NOT NULL,
                principal TEXT NOT NULL,
                purpose TEXT NOT NULL,
                authorized_context_hash TEXT NOT NULL,
                gateway_logical_call_id TEXT NOT NULL,
                gateway_semantic_commit_id TEXT NOT NULL,
                state TEXT NOT NULL,
                result_json TEXT,
                cost_usd REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(operation_key,gateway_semantic_commit_id)
            );
            CREATE INDEX IF NOT EXISTS idx_cognitive_gateway_call ON cognitive_transactions(gateway_logical_call_id);
            CREATE INDEX IF NOT EXISTS idx_cognitive_subsystem_state ON cognitive_transactions(subsystem,state);
        """)

    def apply(self, operation: CognitiveOperation, gateway_result: ModelExecutionResult,
              mutator: Callable[[sqlite3.Connection, Any], Any], *,
              stage_hook: Callable[[str], None] | None = None) -> CognitiveTransactionResult:
        if gateway_result.state is not ExecutionState.COMMITTED or not gateway_result.semantic_commit_id:
            raise ValueError("cognitive mutation requires a committed gateway result")
        txid = cognitive_transaction_id(operation, gateway_result)
        now = datetime.now(timezone.utc).isoformat()
        context_hash = hashlib.sha256(canonical(sorted(operation.authorized_context_ids)).encode()).hexdigest()
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                prior = self.db.execute("SELECT state,result_json FROM cognitive_transactions WHERE cognitive_transaction_id=?", (txid,)).fetchone()
                if prior and prior["state"] == CognitiveTransactionState.APPLIED.value:
                    self.db.execute("COMMIT")
                    return CognitiveTransactionResult(txid, gateway_result.logical_call_id,
                        gateway_result.semantic_commit_id, CognitiveTransactionState.APPLIED,
                        json.loads(prior["result_json"]), True)
                if not prior:
                    self.db.execute("INSERT INTO cognitive_transactions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (txid,operation.operation_key,operation.subsystem,operation.principal,operation.purpose,
                         context_hash,gateway_result.logical_call_id,gateway_result.semantic_commit_id,
                         CognitiveTransactionState.APPLYING.value,None,gateway_result.cost_usd,now,now))
                else:
                    self.db.execute("UPDATE cognitive_transactions SET state=?,updated_at=? WHERE cognitive_transaction_id=?",
                                    (CognitiveTransactionState.APPLYING.value,now,txid))
                if stage_hook: stage_hook("before_cognitive_mutation")
                value = mutator(self.db, gateway_result.value)
                if stage_hook: stage_hook("after_cognitive_mutation")
                self.db.execute("UPDATE cognitive_transactions SET state=?,result_json=?,updated_at=? WHERE cognitive_transaction_id=?",
                    (CognitiveTransactionState.APPLIED.value,canonical(value),datetime.now(timezone.utc).isoformat(),txid))
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        if stage_hook: stage_hook("after_cognitive_commit")
        return CognitiveTransactionResult(txid,gateway_result.logical_call_id,
            gateway_result.semantic_commit_id,CognitiveTransactionState.APPLIED,value,False)

    def audit(self, cognitive_transaction_id: str) -> Mapping[str, Any] | None:
        with self._lock:
            row=self.db.execute("SELECT * FROM cognitive_transactions WHERE cognitive_transaction_id=?",(cognitive_transaction_id,)).fetchone()
            return dict(row) if row else None

    def cost_by_subsystem(self) -> dict[str, float]:
        with self._lock:
            return {row[0]:row[1] for row in self.db.execute("SELECT subsystem,SUM(cost_usd) FROM cognitive_transactions WHERE state=? GROUP BY subsystem",(CognitiveTransactionState.APPLIED.value,))}

    def close(self) -> None:
        self.db.close()


class GatewayCognitiveTransactionService:
    """Canonical P0 sequence: gateway semantic commit, then cognitive transaction."""
    def __init__(self, gateway: ModelGateway, ledger: CognitiveTransactionLedger):
        self.gateway=gateway; self.ledger=ledger

    def execute(self, operation: CognitiveOperation,
                mutator: Callable[[sqlite3.Connection, Any], Any], *,
                stage_hook: Callable[[str], None] | None = None) -> CognitiveTransactionResult:
        gateway_result=self.gateway.execute(operation.request)
        if not gateway_result.committed:
            raise RuntimeError(f"MODEL_EXECUTION_UNAVAILABLE:{gateway_result.failure.value if gateway_result.failure else 'UNKNOWN'}")
        if stage_hook: stage_hook("after_gateway_commit")
        return self.ledger.apply(operation,gateway_result,mutator,stage_hook=stage_hook)

    def health(self) -> object:
        """Expose the canonical gateway health view to cognitive callers."""
        return self.gateway.health()
