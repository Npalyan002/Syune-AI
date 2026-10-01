"""Deterministic Phase 22 scale generator and lexical-path benchmark."""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import statistics
from dataclasses import asdict, dataclass
from time import perf_counter
import tracemalloc

from syune.retrieval.hybrid import tokens

GENERATOR_VERSION = "phase22-scale-v1"
DEFAULT_SEED = 2201


@dataclass(frozen=True, slots=True)
class ScaleRecord:
    memory_id: str
    text: str
    organization: str
    project: str
    agent: str
    valid_from: int
    revision: int
    state: str


def generate_scale_records(count: int, seed: int = DEFAULT_SEED):
    """Yield records without materializing the entire requested population twice."""
    rng = random.Random(seed)
    states = ("VERIFIED", "ASSERTED", "SUPERSEDED", "INVALIDATED")
    for index in range(count):
        entity = index % max(100, count // 20)
        revision = index % 4
        state = states[revision] if index % 97 == 0 else "VERIFIED"
        noise = rng.randrange(10_000)
        yield ScaleRecord(f"m{index}", f"entity {entity} deployment checkpoint token{index} noise{noise}",
                          f"org-{index % 7}", f"project-{index % 31}", f"agent-{index % 13}",
                          2020 + revision, revision, state)


class ScalePostingIndex:
    def __init__(self): self.postings: dict[str, list[str]] = {}; self.records: dict[str, ScaleRecord] = {}
    def upsert(self, record: ScaleRecord):
        self.records[record.memory_id] = record
        for token in set(tokens(record.text)): self.postings.setdefault(token, []).append(record.memory_id)
    def search(self, query: str, limit: int = 5):
        query_tokens = set(tokens(query)); candidates: dict[str, int] = {}
        for token in query_tokens:
            for memory_id in self.postings.get(token, ()): candidates[memory_id] = candidates.get(memory_id, 0) + 1
        eligible = ((score, mid) for mid, score in candidates.items()
                    if self.records[mid].state not in {"SUPERSEDED", "INVALIDATED"})
        return tuple(mid for _, mid in sorted(eligible, key=lambda item: (-item[0], item[1]))[:limit])
    @property
    def bytes_used(self):
        return sum(len(k.encode()) + sum(len(v.encode()) for v in values) for k, values in self.postings.items())


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[min(len(values)-1, max(0, math.ceil(len(values)*fraction)-1))]


def run_scale(count: int, seed: int = DEFAULT_SEED) -> dict:
    tracemalloc.start(); index = ScalePostingIndex(); started = perf_counter()
    write_latencies = []
    for record in generate_scale_records(count, seed):
        write_started = perf_counter(); index.upsert(record); write_latencies.append((perf_counter()-write_started)*1000)
    build_ms = (perf_counter()-started)*1000; _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    query_latencies = []; tp = retrieved = 0
    # Unique tokens create known positives; lexically similar entity/noise tokens are hard negatives.
    for target in random.Random(seed + 1).sample(range(count), min(200, count)):
        began = perf_counter(); hits = index.search(f"deployment checkpoint token{target}"); query_latencies.append((perf_counter()-began)*1000)
        expected = f"m{target}"
        eligible = index.records[expected].state not in {"SUPERSEDED", "INVALIDATED"}
        tp += int(eligible and expected in hits); retrieved += len(hits)
    relevant = sum(index.records[f"m{i}"].state not in {"SUPERSEDED", "INVALIDATED"}
                   for i in random.Random(seed + 1).sample(range(count), min(200, count)))
    return {"status": "EXECUTED", "records": count, "generator_version": GENERATOR_VERSION, "seed": seed,
            "build_time_ms": build_ms, "incremental_write_p95_ms": percentile(write_latencies, .95),
            "index_size_bytes": index.bytes_used, "peak_memory_bytes": peak,
            "query_p50_ms": percentile(query_latencies,.5), "query_p95_ms": percentile(query_latencies,.95),
            "query_p99_ms": percentile(query_latencies,.99), "candidate_generation_p95_ms": percentile(query_latencies,.95),
            "fusion_reranking_ms": 0.0, "recall": tp/relevant if relevant else 1.0,
            "precision": tp/retrieved if retrieved else 0.0, "context_size_mean": retrieved/len(query_latencies),
            "retrieval_fanout_mean": retrieved/len(query_latencies),
            "scope": "lexical derived-index path; ANN and real embeddings not exercised"}


def run(scales=(10_000, 100_000)) -> dict:
    results = {str(scale): run_scale(scale) for scale in scales}
    payload = {"benchmark_version": "phase22-v1", "generator_version": GENERATOR_VERSION, "seed": DEFAULT_SEED,
               "environment": {"python": platform.python_version(), "platform": platform.platform(),
                               "processor": platform.processor(), "logical_cpu_count": os.cpu_count()},
               "results": results}
    payload["content_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload
