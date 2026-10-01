# SYUNE Phase 09 Domain Activation Profiles v1

## Architecture

Phase 09 adds immutable processing overlays to the Phase 08 Cognitive Core. Every profile uses the same `MemoryRepository`, Retrieval index, and `PlasticityView`. Profiles contain configuration and no canonical entities, learned state, storage handles, routing logic, or executable actions.

`CognitiveRequest.activation_profile` accepts a typed `ActivationProfileId`. Omission resolves GENERAL; unknown explicit IDs fail with `INVALID_PROFILE`. `ProfileRegistry` owns the six version-controlled built-ins, rejects duplicate IDs/names, validates active/core/schema compatibility, and returns immutable contracts.

The built-ins are GENERAL (Phase 08 baseline), CREATIVE (breadth, diversity, alternatives), SYSTEMS (relations, paths, gaps), STRATEGY (conflicts, temporal structure, uncertainty), PRODUCT (direct requirements, constraints, context), and RESEARCH (provenance, source diversity, evidence gaps). These are cognitive modes rather than expertise packs or memory domains.

## Typed overlay and hard limits

Each `ActivationProfile` has a typed ID/version/status plus typed Attention, Retrieval, Inference, Metacognition, budget, and response configurations. It declares allowed and prohibited capabilities, compatibility versions, definition provenance, and a SHA-256 fingerprint over canonical sorted configuration. Built-in semantics are immutable and versioned at `@1`.

Effective budget fields use `min(request, profile, GLOBAL_HARD_LIMITS)`. Clipped fields are reported by `ProfileActivation`. Mandatory provenance and epistemic separation are outside the overlay and cannot be disabled. Callers cannot supply arbitrary profile configuration.

## Cognitive integration

- Retrieval: a per-cycle `RetrievalConfig` is derived through the existing narrow RetrievalService constructor, while reusing the same memory, index, materialization check, and learned-state view. Result count, hops, fanout, provenance, and pattern emphasis stay bounded.
- Attention: directness, activation, shared learned relevance, and deterministic source-diversity contributions are visible per item.
- Inference: the one structural engine runs once; profiles deterministically prioritize its typed records without adding hidden rules or edges.
- Metacognition: typed thresholds and penalties adjust advisory readiness while conflicts, gaps, degradation, and provenance limitations remain visible.
- Response: profiles select bounded counts and explanatory emphasis. All candidates remain advisory and non-executable.

`ProfileDiagnostics` exposes selected ID/name/version, explicit/default source, deterministic activation fingerprint, effective budget, clipped settings, modified dimensions, weights, and profile activation timing. `compare_profiles` runs read-only comparisons against identical state.

## Determinism and safety

Default activation time is a deterministic UTC epoch unless the request supplies temporal context; timestamps never enter the fingerprint. Same request/profile/version/memory/learning/config yields the same ordered semantic result across service reconstruction. Runtime timings remain observational.

Profiles never alter confidence, provenance, Observation semantics, canonical content, LearningLedger, PlasticityOverlay, or profile definitions. Selection is explicit with GENERAL default; keyword classification, self tuning, profile-specific databases/indexes, Council, providers, agents, Control Core, actions, ART-DEP-AI, and expertise packs remain absent.

## Limits

V1 diversity is source based, profile comparison is an in-process diagnostic, and built-ins are compiled typed Python artifacts. Profiles emphasize existing lexical and structural evidence; they do not provide specialist knowledge or determine truth.
