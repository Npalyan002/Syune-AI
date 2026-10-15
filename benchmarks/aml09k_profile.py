"""Component profile for AML-09K; not a retrieval-quality harness."""
from __future__ import annotations

import argparse
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from time import perf_counter

from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import (
    AccessContext, Observation, Principal, Provenance, SecurityEnvelope,
    Source, SQLiteMemoryRepository, authorize,
)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def measure(fn, repetitions: int = 7) -> dict[str, float]:
    values = []
    for _ in range(repetitions):
        started = perf_counter(); fn(); values.append((perf_counter() - started) * 1000)
    ordered = sorted(values)
    return {"median_ms": round(median(values), 3), "min_ms": round(ordered[0], 3),
            "max_ms": round(ordered[-1], 3)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, choices=(3000, 10000), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="aml09k-profile-") as directory:
        repo = SQLiteMemoryRepository(Path(directory) / "memory.sqlite3")
        source = Source(SourceId.new(), "synthetic", "aml09k-profile", NOW)
        provenance = Provenance(ProvenanceId.new(), source.id, NOW)
        repo.put(source)
        envelope = SecurityEnvelope(owner="user:load-user")
        for number in range(args.records):
            repo.put(Observation(
                ObservationId.new(), f"synthetic memory {number} alpha marker", "text",
                provenance, NOW, NOW, Confidence(1), security=envelope,
            ))
        index = InvertedSeedIndex(repo); index.rebuild()
        access = AccessContext(Principal("load-user", "aml"), legacy_local_compatible=False)
        ids = tuple(index.entries)
        eligible = lambda entity_id: index.request_eligible(
            entity_id, access, valid_at=NOW, knowledge_at=NOW, current=True)

        authorization = measure(lambda: [authorize(index.entries[item].security, access) for item in ids])
        visible_corpus = measure(lambda: {item for item in ids if eligible(item)})
        allowed = {item for item in ids if eligible(item)}
        partition = index.policy_partition(access)
        partition_hit = measure(lambda: index.policy_partition(access))
        bm25 = measure(lambda: index.lexical(
            "alpha marker", 32, eligible=allowed.__contains__, partition=partition))
        semantic = measure(lambda: index.semantic("alpha marker", 32, eligible=allowed.__contains__))
        repository = measure(lambda: [repo.get(item) for item in ids], 3)
        service = RetrievalService(repo, index)
        full_request = RecallRequest(RecallCue(text="alpha marker", access_context=access))
        cold_started = perf_counter(); service.recall(full_request)
        cold_full_ms = (perf_counter() - cold_started) * 1000
        full = measure(lambda: service.recall(RecallRequest(RecallCue(
            text="alpha marker", access_context=access,
        ))), 5)

        def concurrent_batch():
            with ThreadPoolExecutor(max_workers=16) as pool:
                tuple(pool.map(lambda _: index.lexical(
                    "alpha marker", 32, eligible=allowed.__contains__), range(16)))

        lock_batch = measure(concurrent_batch, 3)
        report = {
            "records": args.records,
            "authorization_checks": authorization,
            "visible_corpus_construction": visible_corpus,
            "cached_partition_lookup": partition_hit,
            "bm25_authorized_statistics_and_ranking": bm25,
            "semantic_filter_and_overfetch": semantic,
            "repository_get_all": repository,
            "full_recall": full,
            "cold_full_recall_ms": round(cold_full_ms, 3),
            "policy_partition_cache": index.partition_metrics(),
            "index_lock_16_search_batch": lock_batch,
            "graph_endpoint_authorization_note": "covered by bounded activated graph; no graph in AML load fixture",
            "index_generation": {"cursor": index.cursor, "lifecycle_cursor": index.lifecycle_cursor},
        }
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        repo.close()


if __name__ == "__main__":
    main()
