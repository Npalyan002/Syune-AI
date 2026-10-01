# SYUNE Phase 10 Multimodal Study v1

## Architecture

Phase 10 extends the existing hash/revision/checkpoint/Observation pipeline with a provider-neutral `syune.perception` layer. `MediaInspector` performs bounded local container inspection. `PerceptionRouter` selects IMAGE, AUDIO, or VIDEO by media type, always emits deterministic metadata, and optionally invokes an explicitly injected capability provider. Typed `PerceptionRun` and `PerceivedSegment` records are stored in the existing operational StudyRegistry; all encoded entities enter the same canonical `MemoryRepository`.

Text, Markdown, and page-aware PDF continue through the Phase 03 parsers and now also receive deterministic PerceptionRun/PerceivedSegment records. Supported detection targets are `.txt`, `.md`, `.markdown`, `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.wav`, `.mp3`, `.m4a`, `.flac`, `.mp4`, `.mov`, `.mkv`, and `.webm`. Local v1 extracts PNG/JPEG dimensions and WAV duration/sample metadata. Other accepted compressed containers receive validated format/byte metadata; duration, frames, transcript, caption, or scene semantics require an explicit adapter. DOCX/PPTX are unsupported.

## Contracts and provenance

Contracts include source/modality/representation/method/status/determinism enums; text, page, normalized image region, audio millisecond range, video millisecond range, and video frame locators; provider metadata; media metadata; resource limits; perceived segments; perception runs; and metadata-only/cache/persist derived-artifact policy. No artifacts are generated in v1.

Each multimodal Observation traces through its `process_id` and durable registry rows to `PerceivedSegment -> PerceptionRun -> SourceRevision -> SHA-256 source bytes`. `SourceLocator` preserves page, normalized region, timestamp, frame, and range information supported by canonical Memory. Deterministic extraction and model-assisted perception remain explicitly distinct. Provider ID/model/version/config fingerprint/execution location are recorded for assisted segments.

Perceived captions, transcripts, scene descriptions, and metadata are non-epistemic Observations with MemoryTraces. Study never creates Claim, Evidence, or Concept. Provider confidence is perception quality and never factual confidence.

## Idempotency, revision, resume, and failure

Whole-file SHA-256 remains source identity. Rename aliases identical bytes to the same source/revision. Changed bytes create a new revision linked to the old revision. Segment fingerprints include source revision, exact locator, representation, provider/config fingerprint, and content; UUID5 IDs prevent duplicate runs, segments, Observations, and traces.

StudyRegistry persists perception run/component status and segment identity alongside existing block and derived checkpoints. A partial encoded run retains deterministic output. On restart, re-study detects PARTIAL and re-runs the incomplete perception configuration; already encoded blocks are skipped, successful new segments are appended, and a successful run becomes active without duplication. Provider failure is isolated from metadata extraction.

## Resource and security policy

`PerceptionLimits` bounds source bytes, pages, pixels, audio/video duration, keyframes, segments, provider calls, derived bytes, wall time, and retries. V1 enforces byte, pixel, WAV duration, and segment limits in the implemented local paths; unused limits remain typed adapter obligations. Paths remain restricted by Study's configured root. No archive expansion, macros, embedded scripts, shell commands, network client, biometric recognition, face recognition, or speaker identity exists.

Providers are constructor-injected protocols. With none configured, no provider/network call occurs and semantic perception is `UNAVAILABLE`; deterministic metadata still encodes. External execution must be declared in provider metadata. Core Memory, Retrieval, Cognition, and Learning import no provider SDK.

## Integration and limitations

Textual captions/transcripts/scene descriptions/metadata enter the existing lexical index. CognitiveService consumes their Observation IDs in one context. LearningService may apply shared utility/salience to those IDs without rewriting content, timecodes, confidence, or provenance.

V1 has no OCR, keyframe generation, subtitle parser, derived artifact files, FFmpeg dependency, compressed audio duration decoder, or video scene detector. Provider adapters and richer deterministic decoders remain future work; unsupported semantics are reported rather than inferred.
