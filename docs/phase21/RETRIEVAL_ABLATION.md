# Retrieval ablation

Evidence: `docs/evals/phase21/ablation.json` and `tests/phase21/test_hybrid_retrieval.py`.

- Exact: deterministic full-text identity hit.
- Lexical: BM25/postings recovered exact wording.
- Entity: capitalized entity evidence recovered the linked item but weak isolated entity-only queries abstain.
- Semantic: deterministic synonym paraphrases (`automobile/vehicle/car`, `chief/owner`) recovered expected items.
- Associative: existing Phase 18 association and multi-hop families remain passing.
- Full routed hybrid: preserved all benchmark relevant records while removing false selections and enabling abstention.

Semantic results are synthetic; no real-provider quality claim is made.
