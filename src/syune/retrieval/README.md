# retrieval

Candidate generation, activation, and working-memory selection boundary; RAG is one mechanism.

The implementation uses deterministic lexical and structural seeding, bounded association expansion, transient activation, explainable scoring, and working-memory candidate selection. The index is derivative and rebuildable from MemoryRepository. See the [Lean v1 architecture](../../../docs/architecture/LEAN_V1_ARCHITECTURE.md).

An optional narrow read-only `PlasticityView` is an experimental compatibility extension. Learned association, salience, and utility contributions are separate visible score components. Retrieval never imports Learning storage and never records a signal.
