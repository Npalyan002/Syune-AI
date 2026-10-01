# Phase 19 validation

`PHASE_19_STATUS = PASS`

Adversarial coverage includes current/historical/as-of behavior, future knowledge, multiple revisions, out-of-order insertion, late arrival, conflicting sources, contextual difference, verified/unverified policy, invalid/superseded learning guards, missing/orphan provenance quarantine, and SQLite restart.

Public parity: internal Python, public SDK, MCP, and host-facing serialized candidates expose query mode, validity/knowledge timestamps, verification policy, truth state, contradiction state, temporal validity, and provenance validity. The public API version remains backward-compatible v1 through additive optional fields.

Phase 18 harness remains operational and immutable raw PRE/POST evidence is retained. Phase 20 must address the unchanged two permission violations. Semantic contradiction inference without structured facts and abstention quality remain future work.
