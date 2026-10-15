"""Frozen AML-09G evaluation on the public BEIR SciFact test split."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from uuid import NAMESPACE_URL, uuid5

from syune.core import Confidence, ObservationId, ProvenanceId, SourceId
from syune.memory import InMemoryReferenceRepository, Observation, Provenance, Source, TruthMetadata, TruthState
from syune.retrieval import InvertedSeedIndex, QueryMode, RecallCue, RecallRequest, RetrievalService

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
KS = (1, 5, 10, 100)
METRICS = tuple([f"recall@{k}" for k in KS] + [f"precision@{k}" for k in KS] + ["mrr", "ndcg", "empty_result_rate"])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def score(ranked: list[str], relevant: set[str]) -> dict[str, float]:
    row: dict[str, float] = {}
    for k in KS:
        hits = len(set(ranked[:k]) & relevant)
        row[f"recall@{k}"] = hits / len(relevant)
        row[f"precision@{k}"] = hits / k
    row["mrr"] = next((1 / rank for rank, doc_id in enumerate(ranked, 1) if doc_id in relevant), 0.0)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, len(relevant) + 1))
    dcg = sum(1 / math.log2(rank + 1) for rank, doc_id in enumerate(ranked, 1) if doc_id in relevant)
    row["ndcg"] = dcg / ideal
    row["empty_result_rate"] = float(not ranked)
    return row


def aggregate(rows: list[dict[str, object]]) -> dict[str, float]:
    return {metric: round(mean(float(row[metric]) for row in rows), 6) for metric in METRICS}


def bootstrap_ci(rows: list[dict[str, object]], metric: str) -> dict[str, float]:
    rng = random.Random(90907)
    values = sorted(mean(float(rng.choice(rows)[metric]) for _ in rows) for _ in range(5000))
    return {"low": round(values[124], 6), "high": round(values[4874], 6)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--benchmark", default="BEIR SciFact")
    args = parser.parse_args()

    corpus_path = args.dataset / "corpus.jsonl"
    queries_path = args.dataset / "queries.jsonl"
    qrels_path = args.dataset / "qrels" / "test.tsv"
    corpus = load_jsonl(corpus_path)
    queries = {str(q["_id"]): str(q["text"]) for q in load_jsonl(queries_path)}
    qrels: dict[str, set[str]] = defaultdict(set)
    for line in qrels_path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        query_id, corpus_id, score_value = line.split("\t")
        if int(score_value) > 0:
            qrels[query_id].add(corpus_id)

    repo = InMemoryReferenceRepository()
    source = Source(SourceId(uuid5(NAMESPACE_URL, "aml09g-beir-scifact")), "BEIR SciFact", "official-test", NOW)
    repo.put(source)
    ids: dict[str, ObservationId] = {}
    for document in corpus:
        doc_id = str(document["_id"])
        oid = ObservationId(uuid5(NAMESPACE_URL, f"aml09g-scifact:{doc_id}"))
        ids[doc_id] = oid
        title = str(document.get("title", "")).strip()
        body = str(document.get("text", "")).strip()
        text = f"{title}. {body}" if title else body
        repo.put(Observation(
            oid, text, "text",
            Provenance(ProvenanceId(uuid5(NAMESPACE_URL, f"aml09g-scifact-prov:{doc_id}")), source.id, NOW),
            NOW, NOW, Confidence(1), TruthMetadata(TruthState.VERIFIED, recorded_at=NOW),
        ))

    index = InvertedSeedIndex(repo)
    index.rebuild()
    service = RetrievalService(repo, index)
    reverse = {oid: doc_id for doc_id, oid in ids.items()}
    rows: list[dict[str, object]] = []
    for query_id in sorted(qrels):
        recalled = service.recall(RecallRequest(
            RecallCue(text=queries[query_id], query_mode=QueryMode.CURRENT), max_results=100,
        ))
        ranked = [reverse[item.entity_id] for item in recalled.candidates if item.entity_id in reverse]
        rows.append({"id": query_id, "ranked": ranked, **score(ranked, qrels[query_id])})

    overall = aggregate(rows)
    ci95 = {metric: bootstrap_ci(rows, metric) for metric in ("recall@1", "recall@5", "mrr", "ndcg")}
    report = {
        "label": args.label,
        "benchmark": args.benchmark,
        "split": "test",
        "dataset_files_sha256": {p.name: sha256(p) for p in (corpus_path, queries_path, qrels_path)},
        "documents": len(corpus),
        "queries": len(rows),
        "qrels": sum(len(value) for value in qrels.values()),
        "categories": {"factual_scientific_claim": len(rows), "paraphrase": None, "compositional": None, "temporal": None},
        "bootstrap": {"unit": "query (benchmark exposes no source-cluster identifiers)", "samples": 5000, "seed": 90907},
        "overall": overall,
        "ci95": ci95,
        "false_positive_rate": None,
        "abstention_accuracy": None,
        "unsupported_metric_reason": "SciFact test qrels are sparse and contain no explicit irrelevant or unanswerable-query labels.",
        "model_free": True,
        "details": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "details"}, indent=2))


if __name__ == "__main__":
    main()
