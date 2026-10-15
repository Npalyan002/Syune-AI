"""Generate the frozen, independently synthetic AML-09D retrieval corpus."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    cities = ("Alderwick", "Brindleford", "Copperhaven", "Dunmere", "Eastridge")
    vehicles = ("automobile", "roadster", "pickup", "van", "wagon")
    engines = ("Aquila", "Boreas", "Cirrus", "Draco", "Eurus")
    suppliers = ("Kestrel", "Lattice", "Meridian", "Northstar", "Oriole")
    documents: list[dict[str, object]] = []
    queries: list[dict[str, object]] = []
    for number in range(40):
        cluster = f"source-{number:02d}"
        project = f"Project-{chr(65 + number // 10)}{number:02d}"
        city = cities[number % len(cities)]
        vehicle = vehicles[(number + 1) % len(vehicles)]
        engine = engines[(number + 2) % len(engines)]
        old_supplier = suppliers[(number + 3) % len(suppliers)] + f"-{number:02d}"
        new_supplier = suppliers[(number + 4) % len(suppliers)] + f"-{number:02d}"
        prefix = f"d{number:02d}"
        documents.extend([
            {"id": f"{prefix}-location", "cluster": cluster,
             "text": f"{project} operates from {city}."},
            {"id": f"{prefix}-vehicle", "cluster": cluster,
             "text": f"{project} selected a {vehicle} for field transport."},
            {"id": f"{prefix}-engine", "cluster": cluster,
             "text": f"{project} uses the {engine} propulsion engine."},
            {"id": f"{prefix}-supplier-old", "cluster": cluster,
             "text": f"{old_supplier} supplied components to {project}.",
             "valid_from": "2022-01-01T00:00:00Z", "valid_until": "2022-12-31T23:59:59Z"},
            {"id": f"{prefix}-supplier-new", "cluster": cluster,
             "text": f"{new_supplier} supplies components to {project}.",
             "valid_from": "2024-01-01T00:00:00Z"},
            {"id": f"{prefix}-distractor", "cluster": cluster,
             "text": f"{project} publishes a quarterly maintenance schedule."},
        ])
        queries.extend([
            {"id": f"q{number:02d}-factual", "cluster": cluster, "category": "factual",
             "text": f"Which city is the operating base for {project}?",
             "relevant": [f"{prefix}-location"]},
            {"id": f"q{number:02d}-paraphrase", "cluster": cluster, "category": "paraphrase",
             "text": f"What automobile was selected by {project}?",
             "relevant": [f"{prefix}-vehicle"]},
            {"id": f"q{number:02d}-compositional", "cluster": cluster, "category": "compositional",
             "text": f"Return {project}'s operating city together with its propulsion engine.",
             "relevant": [f"{prefix}-location", f"{prefix}-engine"]},
            {"id": f"q{number:02d}-temporal-current", "cluster": cluster, "category": "temporal",
             "text": f"Who is {project}'s current component supplier?",
             "valid_at": "2025-01-01T00:00:00Z", "relevant": [f"{prefix}-supplier-new"],
             "forbidden": [f"{prefix}-supplier-old"]},
            {"id": f"q{number:02d}-temporal-history", "cluster": cluster, "category": "temporal",
             "text": f"Which supplier served {project} during 2022?", "mode": "HISTORICAL",
             "valid_at": "2022-06-01T00:00:00Z", "relevant": [f"{prefix}-supplier-old"],
             "forbidden": [f"{prefix}-supplier-new"]},
        ])
        if number % 4 == 0:
            queries.append({"id": f"q{number:02d}-irrelevant", "cluster": cluster,
                            "category": "irrelevant", "text": f"What lunar cipher belongs to {project}?",
                            "relevant": []})
        if number % 5 == 0:
            secret = f"{prefix}-secret"
            documents.append({"id": secret, "cluster": cluster, "owner": "alice",
                              "text": f"{project} private access code is Quartz-{number:02d}."})
            queries.append({"id": f"q{number:02d}-authorization", "cluster": cluster,
                            "category": "authorization", "principal": "bob",
                            "text": f"What is the private access code for {project}?",
                            "relevant": [], "forbidden": [secret]})
    dataset = {
        "version": "aml09d-independent-v1",
        "provenance": "Deterministically generated synthetic facts; no AML/private evaluator material.",
        "generation_seed": "fixed-enumeration-v1",
        "clusters": 40,
        "documents": documents,
        "queries": queries,
    }
    output = Path("benchmarks/data/aml09d_independent_v1.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dataset, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(documents)} documents, {len(queries)} queries, 40 clusters")


if __name__ == "__main__":
    main()
