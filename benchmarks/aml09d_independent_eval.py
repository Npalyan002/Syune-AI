"""Frozen cluster-aware AML-09D model-free retrieval evaluation."""
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
from syune.memory import (AccessContext, InMemoryReferenceRepository, Observation, Principal,
                          Provenance, SecurityEnvelope, Source, TruthMetadata, TruthState)
from syune.retrieval import InvertedSeedIndex, QueryMode, RecallCue, RecallRequest, RetrievalService

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
KS = (1, 5, 10, 100)
METRICS = tuple([f"recall@{k}" for k in KS] + [f"precision@{k}" for k in KS]
                + ["mrr", "ndcg", "empty_result_rate", "false_positive_rate"])


def dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def score(ranked: list[str], relevant: set[str]) -> dict[str, float]:
    row: dict[str, float] = {}
    for k in KS:
        top = ranked[:k]
        hits = len(set(top) & relevant)
        row[f"recall@{k}"] = hits / len(relevant) if relevant else float(not top)
        row[f"precision@{k}"] = hits / k
    row["mrr"] = next((1 / rank for rank, item in enumerate(ranked, 1) if item in relevant), 0.0)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, len(relevant) + 1))
    dcg = sum(1 / math.log2(rank + 1) for rank, item in enumerate(ranked, 1) if item in relevant)
    row["ndcg"] = dcg / ideal if ideal else float(not ranked)
    row["empty_result_rate"] = float(not ranked)
    row["false_positive_rate"] = (len(set(ranked) - relevant) / len(ranked)) if ranked else 0.0
    return row


def aggregate(rows: list[dict[str, object]]) -> dict[str, float]:
    return {key: round(mean(float(row[key]) for row in rows), 6) for key in METRICS}


def clustered_ci(rows: list[dict[str, object]], metric: str) -> dict[str, float]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["cluster"])].append(row)
    clusters = sorted(grouped)
    rng = random.Random(90401)
    values = []
    for _ in range(5000):
        sample = [item for _ in clusters for item in grouped[rng.choice(clusters)]]
        values.append(mean(float(item[metric]) for item in sample))
    values.sort()
    return {"low": round(values[124], 6), "high": round(values[4874], 6)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("benchmarks/data/aml09d_independent_v1.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    raw = args.dataset.read_bytes()
    dataset = json.loads(raw)
    repo = InMemoryReferenceRepository()
    source = Source(SourceId(uuid5(NAMESPACE_URL, "aml09d-source")), "evaluation", "aml09d-v1", NOW)
    repo.put(source)
    ids: dict[str, ObservationId] = {}
    for doc in dataset["documents"]:
        oid = ObservationId(uuid5(NAMESPACE_URL, f"aml09d:{doc['id']}"))
        ids[doc["id"]] = oid
        repo.put(Observation(
            oid, doc["text"], "text",
            Provenance(ProvenanceId(uuid5(NAMESPACE_URL, f"aml09d-prov:{doc['id']}")), source.id, NOW),
            dt(doc.get("valid_from")) or NOW, NOW, Confidence(1),
            TruthMetadata(TruthState.VERIFIED, recorded_at=NOW,
                          valid_from=dt(doc.get("valid_from")), valid_until=dt(doc.get("valid_until"))),
            security=SecurityEnvelope(owner=doc["owner"]) if doc.get("owner") else None,
        ))
    index = InvertedSeedIndex(repo)
    index.rebuild()
    service = RetrievalService(repo, index)
    reverse = {value: key for key, value in ids.items()}
    details: list[dict[str, object]] = []
    for query in dataset["queries"]:
        access = None
        if query.get("principal"):
            access = AccessContext(Principal(query["principal"], "aml09d"), "evaluation",
                                   legacy_local_compatible=False)
        cue = RecallCue(text=query["text"], query_mode=QueryMode(query.get("mode", "CURRENT")),
                        valid_at=dt(query.get("valid_at")), access_context=access)
        recalled = service.recall(RecallRequest(cue, max_results=100))
        ranked = [reverse[item.entity_id] for item in recalled.candidates if item.entity_id in reverse]
        forbidden = sorted(set(query.get("forbidden", ())) & set(ranked))
        details.append({"id": query["id"], "cluster": query["cluster"],
                        "category": query["category"], "ranked": ranked,
                        "forbidden": forbidden, **score(ranked, set(query["relevant"]))})
    categories = {category: aggregate([row for row in details if row["category"] == category])
                  for category in sorted({str(row["category"]) for row in details})}
    overall = aggregate(details)
    overall["recall@5_cluster_ci95"] = clustered_ci(details, "recall@5")
    overall["mrr_cluster_ci95"] = clustered_ci(details, "mrr")
    report = {"label": args.label, "dataset_version": dataset["version"],
              "dataset_sha256": hashlib.sha256(raw).hexdigest(),
              "documents": len(dataset["documents"]), "queries": len(details),
              "clusters": dataset["clusters"], "model_free": True,
              "bootstrap": {"unit": "source cluster", "samples": 5000},
              "overall": overall, "by_category": categories,
              "forbidden_result_count": sum(len(row["forbidden"]) for row in details),
              "details": details}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key != "details"}, indent=2))


if __name__ == "__main__":
    main()
