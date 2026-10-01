"""Storage-agnostic StudyRegistry and local SQLite operational reference adapter."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Protocol

from syune.core import SourceId, SourceVersionId, utc_now
from .errors import StudyError, StudyErrorCode
from .model import (
    Classification, PerceivedBlock, SourceRevisionId, StudyJobId,
    StudyRunId, StudyState, StudyStatus,
)

_TRANSITIONS: dict[StudyState, set[StudyState]] = {
    StudyState.DISCOVERED: {StudyState.REGISTERED},
    StudyState.REGISTERED: {StudyState.PARSING},
    StudyState.PARSING: {StudyState.PERCEIVED},
    StudyState.PERCEIVED: {StudyState.UNDERSTOOD, StudyState.PARSING},
    StudyState.UNDERSTOOD: {StudyState.ENCODED, StudyState.PARSING},
    StudyState.ENCODED: {StudyState.CONSOLIDATING},
    StudyState.CONSOLIDATING: {StudyState.CONSOLIDATED},
    StudyState.CONSOLIDATED: {StudyState.VERIFIED},
    StudyState.VERIFIED: set(),
    StudyState.FAILED: {StudyState.PARSING},
    StudyState.REJECTED: set(),
    StudyState.RETRACTED: set(),
}


class StudyRegistry(Protocol):
    def by_fingerprint(self, digest: str) -> StudyStatus | None: ...
    def by_locator(self, locator: str) -> StudyStatus | None: ...
    def by_source_id(self, source_id: SourceId) -> StudyStatus | None: ...
    def status(self, revision_id: SourceRevisionId) -> StudyStatus: ...
    def create_revision(
        self, *, source_id: SourceId, source_version_id: SourceVersionId,
        revision_id: SourceRevisionId, job_id: StudyJobId, run_id: StudyRunId,
        digest: str, classification: Classification,
        previous_revision_id: SourceRevisionId | None, locator: str,
        parser_version: str, pipeline_version: str,
        block_scheme_version: str, encoder_version: str,
    ) -> StudyStatus: ...
    def add_alias(self, revision_id: SourceRevisionId, locator: str) -> None: ...
    def transition(self, revision_id: SourceRevisionId, state: StudyState) -> None: ...
    def transition_history(self, revision_id: SourceRevisionId) -> tuple[tuple[str, str], ...]: ...
    def set_blocks(self, revision_id: SourceRevisionId, blocks: tuple[PerceivedBlock, ...]) -> None: ...
    def block_fingerprints(self, revision_id: SourceRevisionId) -> tuple[tuple[str, str], ...]: ...
    def has_encoded_block(self, revision_id: SourceRevisionId, block_key: str) -> bool: ...
    def record_encoded(self, revision_id: SourceRevisionId, block_key: str,
                       observation_id: str, trace_id: str) -> None: ...
    def record_failure(self, revision_id: SourceRevisionId,
                       code: StudyErrorCode, message: str) -> None: ...
    def record_input_failure(self, locator: str, code: StudyErrorCode, message: str) -> None: ...
    def input_failure(self, locator: str) -> tuple[str, str] | None: ...
    def record_perception(self, run, segments) -> None: ...
    def perception_summary(self, revision_id: SourceRevisionId) -> tuple[tuple[str, str], ...]: ...
    def close(self) -> None: ...


class SqliteStudyRegistry:
    """Durable local operational metadata, never the production MemoryRepository."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        version=self._db.execute("PRAGMA user_version").fetchone()[0]
        tables={r[0] for r in self._db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required={"revisions","locators","blocks","derived","transitions","input_failures","perception_runs","perception_segments"}
        if version not in (0,1) or (tables and tables!=required):
            self._db.close()
            raise ValueError("incompatible or incomplete study schema")
        self._db.executescript("""
        CREATE TABLE IF NOT EXISTS revisions (
            revision_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_version_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            previous_revision_id TEXT,
            classification TEXT NOT NULL,
            state TEXT NOT NULL,
            parser_version TEXT NOT NULL,
            pipeline_version TEXT NOT NULL,
            block_scheme_version TEXT NOT NULL,
            encoder_version TEXT NOT NULL,
            blocks_total INTEGER NOT NULL DEFAULT 0,
            blocks_processed INTEGER NOT NULL DEFAULT 0,
            checkpoint TEXT,
            error_code TEXT,
            error_message TEXT,
            first_seen TEXT NOT NULL,
            last_processed TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_revisions_digest ON revisions(sha256);
        CREATE INDEX IF NOT EXISTS idx_revisions_source ON revisions(source_id);
        CREATE TABLE IF NOT EXISTS locators (
            locator TEXT NOT NULL,
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            last_seen TEXT NOT NULL,
            PRIMARY KEY (locator, revision_id)
        );
        CREATE INDEX IF NOT EXISTS idx_locators_locator ON locators(locator);
        CREATE TABLE IF NOT EXISTS blocks (
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            block_key TEXT NOT NULL,
            block_order INTEGER NOT NULL,
            fingerprint TEXT NOT NULL,
            PRIMARY KEY (revision_id, block_key)
        );
        CREATE TABLE IF NOT EXISTS derived (
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            block_key TEXT NOT NULL,
            observation_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            PRIMARY KEY (revision_id, block_key)
        );
        CREATE TABLE IF NOT EXISTS transitions (
            revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            from_state TEXT NOT NULL,
            to_state TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS input_failures (
            locator TEXT PRIMARY KEY,
            error_code TEXT NOT NULL,
            error_message TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS perception_runs (
            run_id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES revisions(revision_id),
            status TEXT NOT NULL, perceiver_id TEXT NOT NULL, config_fingerprint TEXT NOT NULL,
            components TEXT NOT NULL, warnings TEXT NOT NULL, errors TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS perception_segments (
            segment_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES perception_runs(run_id),
            fingerprint TEXT NOT NULL, modality TEXT NOT NULL, representation TEXT NOT NULL,
            locator TEXT NOT NULL, method TEXT NOT NULL
        );
        """)
        self._db.execute("PRAGMA user_version=1")
        self._db.commit()

    def __enter__(self) -> "SqliteStudyRegistry":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    def _status_from_row(self, row: sqlite3.Row) -> StudyStatus:
        rid = row["revision_id"]
        digest = row["sha256"]
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("corrupt source fingerprint")
        if row["blocks_total"]<0 or row["blocks_processed"]<0:
            raise ValueError("corrupt study counters")
        locators = tuple(x[0] for x in self._db.execute(
            "SELECT locator FROM locators WHERE revision_id=? ORDER BY locator", (rid,)))
        derived = tuple(value for pair in self._db.execute(
            "SELECT observation_id, trace_id FROM derived WHERE revision_id=? ORDER BY block_key", (rid,))
            for value in pair)
        encoded = self._db.execute(
            "SELECT COUNT(*) FROM derived WHERE revision_id=?", (rid,)).fetchone()[0]
        return StudyStatus(
            SourceId.parse(row["source_id"]), SourceVersionId.parse(row["source_version_id"]),
            SourceRevisionId.parse(rid), StudyJobId.parse(row["job_id"]),
            StudyRunId.parse(row["run_id"]), Classification(row["classification"]),
            StudyState(row["state"]), row["sha256"],
            SourceRevisionId.parse(row["previous_revision_id"]) if row["previous_revision_id"] else None,
            locators, row["parser_version"], row["pipeline_version"],
            row["block_scheme_version"], row["encoder_version"],
            row["blocks_total"], row["blocks_processed"], encoded, derived,
            row["checkpoint"], row["error_code"], row["error_message"],
            datetime.fromisoformat(row["first_seen"]),
            datetime.fromisoformat(row["last_processed"]) if row["last_processed"] else None,
        )

    def status(self, revision_id: SourceRevisionId) -> StudyStatus:
        row = self._db.execute("SELECT * FROM revisions WHERE revision_id=?", (str(revision_id),)).fetchone()
        if row is None:
            raise KeyError(revision_id)
        return self._status_from_row(row)

    def by_fingerprint(self, digest: str) -> StudyStatus | None:
        row = self._db.execute(
            "SELECT * FROM revisions WHERE sha256=? ORDER BY CASE WHEN state='ENCODED' THEN 0 ELSE 1 END, rowid DESC LIMIT 1",
            (digest,)).fetchone()
        return self._status_from_row(row) if row else None

    def by_locator(self, locator: str) -> StudyStatus | None:
        row = self._db.execute(
            """SELECT r.* FROM revisions r JOIN locators l ON r.revision_id=l.revision_id
               WHERE l.locator=? ORDER BY l.last_seen DESC, r.rowid DESC LIMIT 1""",
            (locator,)).fetchone()
        return self._status_from_row(row) if row else None

    def by_source_id(self, source_id: SourceId) -> StudyStatus | None:
        row = self._db.execute(
            "SELECT * FROM revisions WHERE source_id=? ORDER BY rowid DESC LIMIT 1",
            (str(source_id),)).fetchone()
        return self._status_from_row(row) if row else None

    def create_revision(self, *, source_id: SourceId, source_version_id: SourceVersionId,
                        revision_id: SourceRevisionId, job_id: StudyJobId, run_id: StudyRunId,
                        digest: str, classification: Classification,
                        previous_revision_id: SourceRevisionId | None, locator: str,
                        parser_version: str, pipeline_version: str,
                        block_scheme_version: str, encoder_version: str) -> StudyStatus:
        now = utc_now().isoformat()
        with self._db:
            self._db.execute(
                """INSERT INTO revisions
                   (revision_id,source_id,source_version_id,job_id,run_id,sha256,
                    previous_revision_id,classification,state,parser_version,pipeline_version,
                    block_scheme_version,encoder_version,first_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(revision_id), str(source_id), str(source_version_id), str(job_id),
                 str(run_id), digest, str(previous_revision_id) if previous_revision_id else None,
                 classification.value, StudyState.REGISTERED.value, parser_version,
                 pipeline_version, block_scheme_version, encoder_version, now),
            )
            self._db.execute(
                "INSERT INTO locators(locator,revision_id,last_seen) VALUES(?,?,?)",
                (locator, str(revision_id), now),
            )
            self._db.execute(
                "INSERT INTO transitions(revision_id,from_state,to_state,occurred_at) VALUES(?,?,?,?)",
                (str(revision_id), StudyState.DISCOVERED.value, StudyState.REGISTERED.value, now),
            )
        return self.status(revision_id)

    def add_alias(self, revision_id: SourceRevisionId, locator: str) -> None:
        now = utc_now().isoformat()
        with self._db:
            self._db.execute(
                """INSERT INTO locators(locator,revision_id,last_seen) VALUES(?,?,?)
                   ON CONFLICT(locator,revision_id) DO UPDATE SET last_seen=excluded.last_seen""",
                (locator, str(revision_id), now),
            )

    def transition(self, revision_id: SourceRevisionId, state: StudyState) -> None:
        current = self.status(revision_id).state
        allowed = _TRANSITIONS[current] | ({StudyState.FAILED, StudyState.REJECTED, StudyState.RETRACTED}
                                            if current not in {StudyState.VERIFIED, StudyState.REJECTED, StudyState.RETRACTED}
                                            else set())
        if state not in allowed:
            raise StudyError(StudyErrorCode.INVALID_TRANSITION, f"{current.value} -> {state.value}")
        now = utc_now().isoformat()
        with self._db:
            self._db.execute(
                "UPDATE revisions SET state=?,last_processed=? WHERE revision_id=?",
                (state.value, now, str(revision_id)),
            )
            self._db.execute(
                "INSERT INTO transitions(revision_id,from_state,to_state,occurred_at) VALUES(?,?,?,?)",
                (str(revision_id), current.value, state.value, now),
            )

    def transition_history(self, revision_id: SourceRevisionId) -> tuple[tuple[str, str], ...]:
        return tuple((row[0], row[1]) for row in self._db.execute(
            "SELECT from_state,to_state FROM transitions WHERE revision_id=? ORDER BY rowid",
            (str(revision_id),)))

    def set_blocks(self, revision_id: SourceRevisionId, blocks: tuple[PerceivedBlock, ...]) -> None:
        with self._db:
            for block in blocks:
                if block.source_revision_id != revision_id:
                    raise ValueError("block belongs to another revision")
                self._db.execute(
                    """INSERT INTO blocks(revision_id,block_key,block_order,fingerprint)
                       VALUES(?,?,?,?)
                       ON CONFLICT(revision_id,block_key) DO UPDATE SET
                       block_order=excluded.block_order,fingerprint=excluded.fingerprint""",
                    (str(revision_id), block.key, block.order, block.fingerprint),
                )
            self._db.execute(
                "UPDATE revisions SET blocks_total=?,blocks_processed=? WHERE revision_id=?",
                (len(blocks), len(blocks), str(revision_id)),
            )

    def block_fingerprints(self, revision_id: SourceRevisionId) -> tuple[tuple[str, str], ...]:
        return tuple((row[0], row[1]) for row in self._db.execute(
            "SELECT block_key,fingerprint FROM blocks WHERE revision_id=? ORDER BY block_order",
            (str(revision_id),)))

    def has_encoded_block(self, revision_id: SourceRevisionId, block_key: str) -> bool:
        return self._db.execute(
            "SELECT 1 FROM derived WHERE revision_id=? AND block_key=?",
            (str(revision_id), block_key)).fetchone() is not None

    def record_encoded(self, revision_id: SourceRevisionId, block_key: str,
                       observation_id: str, trace_id: str) -> None:
        with self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO derived(revision_id,block_key,observation_id,trace_id) VALUES(?,?,?,?)",
                (str(revision_id), block_key, observation_id, trace_id),
            )
            self._db.execute(
                "UPDATE revisions SET checkpoint=?,last_processed=? WHERE revision_id=?",
                (block_key, utc_now().isoformat(), str(revision_id)),
            )

    def record_failure(self, revision_id: SourceRevisionId,
                       code: StudyErrorCode, message: str) -> None:
        self.transition(revision_id, StudyState.FAILED)
        with self._db:
            self._db.execute(
                "UPDATE revisions SET error_code=?,error_message=? WHERE revision_id=?",
                (code.value, message, str(revision_id)),
            )

    def record_input_failure(self, locator: str, code: StudyErrorCode, message: str) -> None:
        with self._db:
            self._db.execute(
                """INSERT INTO input_failures(locator,error_code,error_message,occurred_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT(locator) DO UPDATE SET error_code=excluded.error_code,
                   error_message=excluded.error_message,occurred_at=excluded.occurred_at""",
                (locator, code.value, message, utc_now().isoformat()),
            )

    def input_failure(self, locator: str) -> tuple[str, str] | None:
        row = self._db.execute(
            "SELECT error_code,error_message FROM input_failures WHERE locator=?", (locator,)).fetchone()
        return (row[0], row[1]) if row else None

    def record_perception(self, run, segments) -> None:
        import json
        with self._db:
            self._db.execute("INSERT OR REPLACE INTO perception_runs VALUES(?,?,?,?,?,?,?,?)",(str(run.id),str(run.source_revision_id),run.status.value,run.perceiver_id,run.config_fingerprint,json.dumps([(a,b.value) for a,b in run.components]),json.dumps(run.warnings),json.dumps(run.errors)))
            for segment in segments:
                self._db.execute("INSERT OR IGNORE INTO perception_segments VALUES(?,?,?,?,?,?,?)",(str(segment.id),str(run.id),segment.fingerprint,segment.modality.value,segment.representation.value,repr(segment.locator),segment.method.value))

    def perception_summary(self, revision_id: SourceRevisionId) -> tuple[tuple[str, str], ...]:
        from syune.perception.model import RunStatus
        rows = tuple((row[0],row[1]) for row in self._db.execute("SELECT run_id,status FROM perception_runs WHERE revision_id=? ORDER BY rowid",(str(revision_id),)))
        for _, status in rows: RunStatus(status)
        return rows
