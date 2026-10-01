# SYUNE Phase 03 - Study System v1

**Scope:** deterministic local perception and safe encoding for UTF-8 TXT, Markdown, and text-based PDF. **Mode:** L1 ADVISORY. Source content is untrusted data.

## Architecture and lifecycle

`StudyService` orchestrates a synchronous explicit source-study call. It reads source bytes without modifying them, hashes them with SHA-256, classifies the content, parses canonical `PerceivedBlock` objects, records operational progress in `StudyRegistry`, then uses `StudyEncoder` for `PerceivedBlock -> Observation -> MemoryTrace`. `syune.study` depends on `syune.core` and `syune.memory`; Memory has no Study import.

All canonical lifecycle states are representable. V1 progresses through REGISTERED, PARSING, PERCEIVED, UNDERSTOOD, and ENCODED. The v1 meaning of UNDERSTOOD is **structural interpretation ready for encoding**, never epistemic acceptance. CONSOLIDATING, CONSOLIDATED, and VERIFIED are not claimed. FAILED persists errors. `is_studied` means the exact content revision reached ENCODED with every parsed block ledgered, not that any source assertion is true.

## Identity, fingerprints, and versions

Whole-source identity uses SHA-256 of bytes, independent of path/name. Locators are aliases in operational metadata, never primary cognitive IDs. Typed `SourceId`, `SourceVersionId`, `SourceRevisionId`, `StudyJobId`, and `StudyRunId` distinguish source, version, revision, job, and run. Canonical blocks have deterministic keys/typed IDs and SHA-256 text fingerprints. Pipeline, parser, block-fingerprint scheme, and encoder versions are recorded. Changed bytes at the same locator create a new revision linked to the prior one; old provenance and ledger entries remain.

Classifications are NEW_SOURCE, ALREADY_STUDIED, CHANGED_SOURCE, and INCOMPLETE. Exact completed content is skipped and may gain another locator alias. Incomplete matching-version work resumes with the same revision/job/checkpoint. Incompatible incomplete versions start a linked new revision while retaining the old run. Block comparison uses sequence alignment of stored fingerprints to report UNCHANGED, NEW, CHANGED, and REMOVED structurally; it performs no semantic Retrieval.

## Registry and status

`StudyRegistry` is storage-agnostic. `SqliteStudyRegistry` is the local durable reference implementation using Python stdlib sqlite3, configurable by path; `.syune/state/` is the recommended gitignored state area. Its schema is internal, not a public compatibility contract or production MemoryRepository choice. It stores revisions, aliases, version metadata, block fingerprints, lifecycle transition history, checkpoints, failures, and a derived-ID ledger. Status can be queried by source ID, locator, or fingerprint. Pre-registration input failures are separately queryable by locator.

The operational registry survives process restart and remembers exact-content study status and derived IDs. The Phase 02 in-memory MemoryRepository remains ephemeral; this phase does not make memory objects themselves durable across restart. Production MemoryRepository persistence remains a separate future decision.

## Parsers and provenance

TXT and Markdown are UTF-8-first, including UTF-8 BOM; invalid UTF-8, binary controls, empty/no-usable text fail explicitly. There is no legacy encoding fallback. TXT splits on blank lines and records line spans. Markdown preserves heading paths, section/line/block locators, and code fences as literal data; links and images are not fetched. `pypdf` extracts only text from pages and records page/block locators. Encrypted, unreadable, or no-text PDFs fail and are never marked studied. OCR, image/audio/video processing, web fetches, and document execution are absent.

Each `Observation` carries SourceId, SourceVersionId, exact available locator, process/pipeline metadata, and UTC timestamps through `Provenance`. `MemoryTrace` references ObservationId. Observation extraction confidence is unknown unless separately measured; MemoryTrace's confidence records successful structural encoding only, never truth of the text. No Claim or Concept is automatically created. Deterministic IDs and block checkpoints make retry idempotent. The ledger records both ObservationId and MemoryTraceId per block.

## Security and limits

Source paths are resolved and optionally constrained to a configured library root. Sources are opened read-only. Parser content is never executed, links are never followed, and no network, LLM, MCP, retrieval, agent dispatch, or Executive behavior exists. Registry state is local and gitignored.

The operational registry's durable ledger is not a durable MemoryRepository. Retraction propagation, epistemic evaluation, semantic interpretation, cognitive consolidation, and associative retrieval are deferred. Future phases may derive Concepts/Claims from Observations only under their own contracts and provenance rules.
