# retrieval

Candidate generation, activation, and working-memory selection boundary; RAG is one mechanism.

Phase 04 implements deterministic lexical and structural seeding, bounded association expansion, transient activation, explainable scoring, and working-memory candidate selection. The index is derivative and rebuildable from MemoryRepository. See `docs/PHASE_04_RETRIEVAL_ASSOCIATIVE_ACTIVATION.md`.

Phase 07 adds an optional narrow read-only `PlasticityView`. Learned association, salience, and utility contributions are separate visible score components. Retrieval never imports Learning storage and never records a signal.
