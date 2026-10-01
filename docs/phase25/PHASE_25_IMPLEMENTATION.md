# Phase 25 implementation

Status: `PASS` for controlled deterministic evidence; this is not production-model proof.

Phase 25 closes canonical gap **G10** and exercises the same-target portion of **G28**. `OrganizationalLearningService` is the sole transfer mediator. Agents submit agent-private `SharedExperience`; they never write another agent's memory. Promotion materializes only a derived `Procedure` protected by the Phase 20 security envelope and served by ordinary Phase 21/22 retrieval. Phase 24 local learning remains unchanged and is still the default.

The durable store separates private experience rows, organizational knowledge, scope-expansion audit, and events. Cross-agent maintenance is explicit/offline; ordinary recall never performs learning analysis. No weights, fine-tuning, broadcast, distributed consensus, or Phase 26 architecture was added.

Implemented production contracts are in `src/syune/learning/organizational.py`; exports are in `src/syune/learning/__init__.py`. Tests and benchmark evidence are under `tests/phase25`, `benchmarks/phase25.py`, and `docs/evals/phase25`.
