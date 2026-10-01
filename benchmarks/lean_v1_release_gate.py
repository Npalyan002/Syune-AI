"""Validation-only operational and scale measurements for the frozen Lean v1 gate."""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from time import sleep
from uuid import UUID

from syune import ContextRequest, RememberRequest, RuntimeMode, Syune
from syune.context import ContextService
from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import Observation, Provenance, SQLiteMemoryRepository, Source
from syune.product.config import load_config
from syune.product.runtime import SyuneRuntime
from syune.product.state import DATABASES, initialize_state
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService


NOW = datetime(2026, 9, 29, tzinfo=timezone.utc)


def pct(values, fraction):
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * fraction))]


def summary(values):
    return {"p50_ms": round(statistics.median(values), 3), "p95_ms": round(pct(values, .95), 3),
            "p99_ms": round(pct(values, .99), 3)}


def row_counts(path):
    with sqlite3.connect(path) as db:
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {name: db.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
                for name in ("entities", "change_journal", "lifecycle", "lifecycle_events") if name in names}


def operational(root: Path):
    root = root.resolve()
    config = load_config(cli_state_root=root); initialize_state(config)
    startup, thread_counts, startup_errors = [], [], []
    for _ in range(25):
        before = threading.active_count(); started = perf_counter()
        try:
            with SyuneRuntime.open(config) as runtime:
                startup.append((perf_counter() - started) * 1000)
                thread_counts.append(threading.active_count() - before)
                assert runtime.learning is runtime.cognition is runtime.council is runtime.planner is None
        except OSError as exc:
            startup_errors.append(type(exc).__name__)
        sleep(.05)
    memory_path = root / DATABASES["memory"]
    with Syune.open(state_root=root, mode=RuntimeMode.TEST) as client:
        remembered = client.remember(RememberRequest("release gate provenance record"))
        before = row_counts(memory_path)
        context = client.context(ContextRequest("release gate provenance", max_chars=1000))
        after_context = row_counts(memory_path)
        audit_before_restart = client.audit().data
        item_fields = sorted(context.data["items"][0])
        client.forget(remembered.data["memory_id"])
        after_forget = row_counts(memory_path)
    with Syune.open(state_root=root, mode=RuntimeMode.TEST) as restarted:
        audit_after_restart = restarted.audit().data
        forgotten_after_restart = restarted.context("release gate provenance").data["items"]
    return {
        "startup": summary(startup) if startup else None, "startup_failures": startup_errors,
        "background_threads_delta": max(thread_counts, default=0),
        "default_repositories_opened": 2,
        "initialized_services": ["memory", "study_registry", "index", "retrieval", "context", "study"],
        "state_database_files": sorted(str(path.relative_to(root)) for path in root.rglob("*.sqlite3")),
        "context_item_fields": item_fields,
        "audit_before_restart": audit_before_restart,
        "audit_after_restart": audit_after_restart,
        "forgotten_visible_after_restart": bool(forgotten_after_restart),
        "writes": {
            "context": {key: after_context.get(key, 0) - before.get(key, 0) for key in before},
            "forget": {key: after_forget.get(key, 0) - after_context.get(key, 0) for key in before},
        },
    }


def scale(root: Path, count: int, repeats: int):
    root.mkdir(parents=True, exist_ok=True); path = root / f"memory-{count}.sqlite3"
    source_id = SourceId(UUID(int=1)); provenance = Provenance(ProvenanceId(UUID(int=2)), source_id, NOW,
        process_id="lean-v1-release-gate", pipeline_version="1")
    with SQLiteMemoryRepository(path) as repo:
        if repo.entity_count() == 0:
            repo.put(Source(source_id, "synthetic", "lean-v1-release-gate", NOW))
            batch = tuple(Observation(ObservationId(UUID(int=100 + position)),
                f"common validation record {position} marker-{position} project-{position % 97}", "text",
                provenance, NOW, NOW, Confidence(1.0)) for position in range(count))
            write_started = perf_counter(); repo.put_many(batch); write_ms = (perf_counter() - write_started) * 1000
        else:
            write_ms = 0.0
        index = InvertedSeedIndex(repo); build_started = perf_counter(); index.rebuild()
        build_ms = (perf_counter() - build_started) * 1000
        service = RetrievalService(repo, index); context_service = ContextService(repo, service)
        selective, broad, contexts, strong_selective, strong_broad = [], [], [], [], []
        for position in range(repeats + 2):
            started = perf_counter(); index.lexical(f"marker-{count // 2}", 32)
            if position >= 2: strong_selective.append((perf_counter() - started) * 1000)
            started = perf_counter(); service.recall(RecallRequest(RecallCue(text=f"marker-{count // 2}"), max_results=8))
            if position >= 2: selective.append((perf_counter() - started) * 1000)
            started = perf_counter(); index.semantic("similar common validation record", 32)
            if position >= 2: strong_broad.append((perf_counter() - started) * 1000)
            started = perf_counter(); service.recall(RecallRequest(RecallCue(text="similar common validation record"), max_results=8))
            if position >= 2: broad.append((perf_counter() - started) * 1000)
            started = perf_counter(); context_service.assemble(RecallRequest(RecallCue(text=f"marker-{count // 2}"), max_results=8), max_chars=8000)
            if position >= 2: contexts.append((perf_counter() - started) * 1000)
        stats = index.health()
    return {"records": count, "write_ms": round(write_ms, 3), "index_build_ms": round(build_ms, 3),
            "selective": summary(selective), "broad": summary(broad), "context": summary(contexts),
            "strong_rag_selective": summary(strong_selective), "strong_rag_broad": summary(strong_broad),
            "p95_overhead": {
                "selective_absolute_ms": round(pct(selective,.95)-pct(strong_selective,.95),3),
                "selective_percent": round((pct(selective,.95)/max(.001,pct(strong_selective,.95))-1)*100,1),
                "broad_absolute_ms": round(pct(broad,.95)-pct(strong_broad,.95),3),
                "broad_percent": round((pct(broad,.95)/max(.001,pct(strong_broad,.95))-1)*100,1)},
            "generated_candidates_last": index.generated_candidates,
            "vector_backend": stats.backend, "vector_bytes": stats.indexed_vectors * 64 * 8 if stats.indexed_vectors else 0,
            "memory_bytes": path.stat().st_size, "bytes_per_record": round(path.stat().st_size / count, 2)}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path)
    parser.add_argument("--scale", type=int); parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    result = scale(args.root, args.scale, args.repeats) if args.scale else operational(args.root)
    json.dump(result, sys.stdout, indent=2, sort_keys=True); print()


if __name__ == "__main__": main()
