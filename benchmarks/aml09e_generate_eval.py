"""Generate AML-09E source-disjoint development and untouched final corpora."""
from __future__ import annotations
import json
from pathlib import Path


def main() -> None:
    docs, queries = [], []
    places = ("Cedarport", "Elmstead", "Foxhaven", "Glenmoor", "Highridge", "Ironbay")
    states = ("amber", "blue", "coral", "green", "silver", "violet")
    for number in range(48):
        split = "development" if number < 24 else "final"
        local = number if split == "development" else number - 24
        cluster = f"{split}-source-{local:02d}"
        entity = (f"Orchid-{local:02d}" if split == "development" else f"Helix-{local:02d}")
        place, state = places[local % 6], states[(local + 2) % 6]
        person = (f"Mira-{local:02d}" if split == "development" else f"Nila-{local:02d}")
        material = ("titanium" if local % 2 == 0 else "ceramic")
        p = f"{split[0]}{local:02d}"
        if split == "development":
            facts = [
                ("place", f"{entity} headquarters is in {place}."),
                ("person", f"{person} coordinates {entity}."),
                ("material", f"{entity} uses a {material} housing."),
                ("old", f"{entity} status was red.", "2022-01-01T00:00:00Z", "2022-12-31T23:59:59Z"),
                ("new", f"{entity} status is {state}.", "2024-01-01T00:00:00Z", None),
                ("noise", f"{entity} publishes monthly maintenance notes."),
            ]
            q = [
                ("factual", f"Where is the headquarters of {entity}?", ["place"]),
                ("paraphrase", f"Who manages {entity}?", ["person"]),
                ("compositional", f"Return the headquarters and housing material for {entity}.", ["place", "material"]),
                ("temporal-current", f"What is the current status of {entity}?", ["new"]),
                ("temporal-history", f"What was the status of {entity} in 2022?", ["old"]),
                ("irrelevant", f"What launch password belongs to {entity}?", []),
            ]
        else:
            facts = [
                ("place", f"{entity} keeps its base station at {place}."),
                ("person", f"{person} is responsible for {entity}."),
                ("material", f"{entity} has a {material} outer shell."),
                ("old", f"{entity} phase was red.", "2022-01-01T00:00:00Z", "2022-12-31T23:59:59Z"),
                ("new", f"{entity} phase is {state}.", "2024-01-01T00:00:00Z", None),
                ("noise", f"{entity} issues routine service bulletins."),
            ]
            q = [
                ("factual", f"Which base station belongs to {entity}?", ["place"]),
                ("paraphrase", f"Who is the chief of {entity}?", ["person"]),
                ("compositional", f"Return the base station and outer shell of {entity}.", ["place", "material"]),
                ("temporal-current", f"What is the current phase of {entity}?", ["new"]),
                ("temporal-history", f"What was the phase of {entity} in 2022?", ["old"]),
                ("irrelevant", f"What encryption password belongs to {entity}?", []),
            ]
        ids = {}
        for fact in facts:
            kind, text, *validity = fact
            doc = {"id": f"{p}-{kind}", "cluster": cluster, "split": split, "text": text}
            if validity:
                doc["valid_from"] = validity[0]
                if validity[1]: doc["valid_until"] = validity[1]
            docs.append(doc); ids[kind] = doc["id"]
        for category, text, relevant in q:
            query = {"id": f"q-{p}-{category}", "cluster": cluster, "split": split,
                     "category": "temporal" if category.startswith("temporal") else category,
                     "text": text, "relevant": [ids[item] for item in relevant]}
            if category == "temporal-current":
                query.update(valid_at="2025-01-01T00:00:00Z", forbidden=[ids["old"]])
            if category == "temporal-history":
                query.update(valid_at="2022-06-01T00:00:00Z", mode="HISTORICAL", forbidden=[ids["new"]])
            queries.append(query)
        if local % 6 == 0:
            secret = {"id": f"{p}-secret", "cluster": cluster, "split": split, "owner": "alice",
                      "text": f"{entity} confidential seal is Quartz-{local:02d}."}
            docs.append(secret)
            queries.append({"id": f"q-{p}-authorization", "cluster": cluster, "split": split,
                            "category": "authorization", "principal": "bob",
                            "text": f"What confidential seal belongs to {entity}?",
                            "relevant": [], "forbidden": [secret["id"]]})
    result = {"version": "aml09e-independent-v1", "clusters": 48,
              "provenance": "Deterministically generated independent synthetic corpus; no AML/private material.",
              "documents": docs, "queries": queries}
    path = Path("benchmarks/data/aml09e_independent_v1.json")
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"documents={len(docs)} queries={len(queries)} clusters=48")


if __name__ == "__main__": main()
