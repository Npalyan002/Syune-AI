"""Frozen, model-free AML-09C retrieval evaluation (public + synthetic data)."""
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
                + ["mrr", "ndcg", "empty", "false_positive_rate"])


def dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def score_query(ranked: list[str], relevant: set[str], acceptable: set[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for k in KS:
        top = ranked[:k]
        hits = len(set(top) & relevant)
        result[f"recall@{k}"] = hits / len(relevant) if relevant else float(not top)
        result[f"precision@{k}"] = len(set(top) & (relevant | acceptable)) / k
    result["mrr"] = next((1 / rank for rank, item in enumerate(ranked, 1) if item in relevant), 0.0)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, len(relevant) + 1))
    dcg = sum(1 / math.log2(rank + 1) for rank, item in enumerate(ranked, 1) if item in relevant)
    result["ndcg"] = dcg / ideal if ideal else float(not ranked)
    result["empty"] = float(not ranked)
    result["false_positive_rate"] = (len(set(ranked) - relevant - acceptable) / len(ranked)) if ranked else 0.0
    return result


def aggregate(rows: list[dict[str, float]]) -> dict[str, float]:
    return {key: round(mean(row[key] for row in rows), 6) for key in METRICS} if rows else {}


def bootstrap(rows: list[dict[str, float]], key: str) -> dict[str, float]:
    rng = random.Random(90210)
    values = sorted(mean(rng.choice(rows)[key] for _ in rows) for _ in range(1000))
    return {"low": round(values[24], 6), "high": round(values[974], 6)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("benchmarks/data/aml09c_retrieval_v1.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    raw = args.dataset.read_bytes(); dataset = json.loads(raw)
    repo = InMemoryReferenceRepository()
    source = Source(SourceId(uuid5(NAMESPACE_URL, "aml09c-source")), "evaluation", "aml09c-v1", NOW)
    repo.put(source); ids = {}
    for doc in dataset["documents"]:
        oid = ObservationId(uuid5(NAMESPACE_URL, f"aml09c:{doc['id']}")); ids[doc["id"]] = oid
        security = SecurityEnvelope(owner=doc["owner"]) if doc.get("owner") else None
        truth = TruthMetadata(TruthState.VERIFIED, recorded_at=NOW,
                              valid_from=dt(doc.get("valid_from")), valid_until=dt(doc.get("valid_until")))
        repo.put(Observation(oid, doc["text"], "text",
            Provenance(ProvenanceId(uuid5(NAMESPACE_URL, f"aml09c-prov:{doc['id']}")), source.id, NOW),
            dt(doc.get("valid_from")) or NOW, NOW, Confidence(1), truth, security=security))
    index = InvertedSeedIndex(repo); index.rebuild(); service = RetrievalService(repo, index)
    details = []
    for query in dataset["queries"]:
        access = None
        if query.get("principal"):
            principal = Principal(query["principal"], "aml09c")
            access = AccessContext(principal, "evaluation", legacy_local_compatible=False)
        cue = RecallCue(text=query["text"], query_mode=QueryMode(query.get("mode", "CURRENT")),
                        valid_at=dt(query.get("valid_at")),
                        access_context=access)
        result = service.recall(RecallRequest(cue, max_results=100))
        reverse = {value: key for key, value in ids.items()}
        ranked = [reverse[item.entity_id] for item in result.candidates if item.entity_id in reverse]
        relevant, acceptable = set(query["relevant"]), set(query.get("acceptable", ()))
        scores = score_query(ranked, relevant, acceptable)
        forbidden = set(query.get("forbidden", ())) & set(ranked)
        details.append({"id": query["id"], "split": query["split"], "category": query["category"],
                        "ranked": ranked, "forbidden": sorted(forbidden), **scores})
    by_split = {}
    for split in ("development", "heldout"):
        rows = [row for row in details if row["split"] == split]
        by_split[split] = aggregate(rows)
        by_split[split]["recall@5_ci95"] = bootstrap(rows, "recall@5")
        by_split[split]["mrr_ci95"] = bootstrap(rows, "mrr")
    categories = {category: aggregate([row for row in details if row["split"] == "heldout" and row["category"] == category])
                  for category in sorted({row["category"] for row in details if row["split"] == "heldout"})}
    report = {"label": args.label, "dataset_version": dataset["version"],
              "dataset_sha256": hashlib.sha256(raw).hexdigest(), "queries": len(details),
              "model_free": True, "splits": by_split, "heldout_by_category": categories,
              "forbidden_result_count": sum(len(row["forbidden"]) for row in details), "details": details}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
