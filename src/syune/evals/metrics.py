"""Small curated retrieval metrics and empirical nearest-rank latency summaries."""
from math import ceil
from statistics import median


def percentiles(values):
    values = sorted(values)
    if not values:
        raise ValueError("samples required")
    return {"p50_ms": median(values), "p95_ms": values[ceil(.95*len(values))-1],
            "p99_ms": values[ceil(.99*len(values))-1], "samples": len(values)}


def retrieval_metrics(ranked, relevant, k, acceptable=()):
    if k < 1 or not relevant:
        raise ValueError("positive K and relevant judgments required")
    top = tuple(ranked[:k])
    if len(set(top)) != len(top):
        raise ValueError("duplicate retrieval identity")
    hits = set(top) & set(relevant)
    allowed = set(relevant) | set(acceptable)
    return {"recall_at_k": len(hits)/len(set(relevant)),
            "precision_at_k": len(set(top) & allowed)/k,
            "mrr": next((1/n for n, item in enumerate(top, 1) if item in relevant), 0),
            "coverage": float(bool(hits)),
            "false_positive_rate": len(set(top)-allowed)/max(1, len(top))}
