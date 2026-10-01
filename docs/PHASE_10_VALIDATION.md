# SYUNE Phase 10 validation

`PHASE_10_STATUS = PASS`

## Changes and dependencies

Added `src/syune/perception` contracts, inspector, provider protocols, router, errors; multimodal Study/registry/encoder integration; tests; benchmark; docs; and architecture rules. Modified core typed IDs, Study contracts, registry schema, service, README, and architecture documentation. Added no Python dependency, external runtime tool, or ADR. FFmpeg, OCR engines, provider SDKs, and network clients are not required.

## Pipeline demonstrations

- Image: synthetic PNG registers with dimensions and whole-image normalized locator; fake local provider caption encodes and recalls; no provider yields metadata plus explicit unavailable state.
- Audio: synthetic 100 ms WAV exposes duration/sample metadata; fake local transcript has exact millisecond range and is retrievable.
- Video: validated synthetic MP4 container emits timestamped metadata; fake local scene description carries an exact time range and is retrievable. No every-frame processing occurs.
- PDF: existing two-page fixture test produces page 1/page 2 Observations with page-aware provenance.
- Rename/idempotency: byte-identical renamed image resolves `ALREADY_STUDIED` with the same source/revision and no duplicate derived entities.
- Revision: changed PNG bytes create `CHANGED_SOURCE`, preserve the prior revision link, and retain old memory.
- Partial/restart: failing video semantics leaves metadata and a durable PARTIAL run; reopening registry with a working provider resumes that configuration, skips existing metadata, adds one scene segment, marks COMPLETE, and subsequent study adds nothing.
- Shared memory: document/image/audio/video Observations use one MemoryRepository and one lexical index. No modality database exists.
- Epistemic boundary: all perceived values remain Observation/MemoryTrace; no Claim is created.
- No silent upload: provider-free test invokes no provider and records semantic `UNAVAILABLE`; the package imports no network client.
- Integration: Retrieval finds caption/transcript/scene text; one CognitiveService context consumes their IDs; shared LearningService targets a caption ID while the Observation content/provenance remain equal.

## Benchmark

Five clean local Study runs per deterministic fixture on Windows/Python 3.12. Provider time is zero and no network is included.

| Fixture | Bytes | Segments | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: |
| Text | 24 | 1 | 60.07 | 64.59 |
| PDF | 673 | 1 | 67.45 | 184.26 |
| PNG | 31 | 1 | 65.56 | 67.47 |
| MP4 | 21 | 1 | 72.36 | 84.44 |
| WAV | 16,044 | 1 | 74.55 | 81.75 |

Inspection, provider, encoding/checkpoint, and total Study boundaries are exposed in perception results and existing Study state. SQLite setup/commit dominates these tiny fixtures; no release threshold is claimed.

## Gates

- Full locked pytest suite: PASS (`111 passed`).
- Phase 10 architecture check: PASS.
- `git diff --check`: PASS.
- Full diff review: PASS.
- Local commit and clean worktree: PASS.
- Remote/push: none.

## Deviations and decisions

Compressed media support is honest container validation plus metadata unless a provider is explicitly supplied. V1 generates no DerivedArtifact, so storage policy is contractual only. PDF stays in the proven Phase 03 page parser. Canonical SourceLocator represents typed perception locators without changing the stable Memory schema. No unresolved issue blocks the milestone.

## Exit checklist

- [x] Source kinds/formats, MediaInspector, router, provider-neutral contracts.
- [x] PerceptionRun, PerceivedSegment, DerivedArtifact, typed locators, methods, confidence boundary.
- [x] Image/audio/video local pipelines and page-aware PDF regression.
- [x] Exact segment/run/revision/hash/locator provenance.
- [x] Observation-only shared Memory encoding; no automatic epistemic promotion.
- [x] Rename idempotency, changed-byte revisioning, stable segment identity.
- [x] Partial component state, isolated provider failure, durable restart/resume, bounded retry contract.
- [x] Resource ceilings, Study-root safety, no shell/macros/archive extraction.
- [x] Explicit provider absence and no silent external upload.
- [x] Retrieval, Cognition, and explicit shared Learning compatibility.
- [x] Benchmark, regression/unit/integration/architecture tests, docs, commit, clean tree.
- [x] No modality memory silo, vectors, biometrics, web ingestion, agents, Council, Control Core, ART-DEP-AI, Executive, Phase 11.
