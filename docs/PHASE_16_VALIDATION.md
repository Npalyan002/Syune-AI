# Phase 16 validation

**Result: PASS for Public Interfaces, SDK & Integration Protocol v1.** Package version remains 0.1.0, public API version is 1, MCP contract version is 1, and state schema remains 1. No dependency or persistent schema changed.

## Surface and safety result

The public facade supports handshake, capabilities, health, status, Study, source status, memory get, Recall, Cognition, Council, and proposal-only Planning. Top-level exports are explicit. The generic host imports only `syune` public symbols; no repository, store, SQLite connection, provider adapter, test utility, or execution implementation is exported. Study applies the same configured-root confinement as MCP.

Public supervised execution is deliberately deferred. `Syune` has no `execute` or `execute_approved`; MCP has no execution tool. Planning returns `execution_authority=false` and preserves the exact approval envelope as data. Phase 13 no-approval, stale/scope-drift, parameter-drift, idempotency, unknown-outcome, stop, circuit, and verification tests remain in the full regression suite. There is no self-approval, generic shell/Python, unrestricted HTTP, REST/cloud service, telemetry, ART-DEP-AI dependency, migration, or L4 behavior.

Stable public errors cover invalid request, not initialized, not found, unavailable, degraded, blocked, approval required, conflict, limit exceeded, unsupported version, and internal failure. Normal SDK/MCP errors are bounded and omit tracebacks. Deterministic JSON uses sorted keys, stable enum values, typed IDs, and UTC ISO-8601 timestamps. Checked-in common result/error JSON schemas and a v1 serialized fixture establish the compatibility baseline.

Version negotiation passes supported v1, unsupported future/no-shared version, invalid input, and additive optional-field behavior. The handshake reports package/public/state versions, L3 supervised autonomy, runtime mode, health, and mode-aware capabilities. NORMAL/TEST advertise Study; READ_ONLY/SHADOW do not. Execution is advertised unavailable with the public-v1 deferral reason.

## Verification evidence

| Gate | Result |
| --- | --- |
| Focused Phase 16 SDK/MCP/contracts/parity | 7 passed; included in final full suite |
| Full test suite | 230 passed in 52.08 s |
| Phase 14 full regression/evals | 230 passed in 45.42 s; READY_WITH_LIMITATIONS |
| Installed wheel generic host | PASS: handshake, Study, Recall, Cognition, Council, Plan |
| Installed wheel MCP | PASS: all 10 v1 tools discovered and exercised |
| SDK/MCP parity | PASS for health, recall entity semantics, cognition status, plan status/authority |
| Runtime-mode restrictions | PASS: SHADOW omits Study and marks it unavailable |
| Detachability/no internal imports | PASS by architecture test and installed example |
| State ownership | PASS: host uses only public operations; no DB path/import in example |
| Approval safety | PASS: execution absent publicly; full Phase 13 regressions pass |
| Architecture checker | PASS |
| `git diff --check` | PASS |
| Artifact audit | PASS: wheel 136,958 bytes/105 files; sdist 111,843 bytes/121 files |

The wheel and sdist built successfully from the source distribution. An isolated CPython 3.12.10 environment installed the wheel plus declared dependencies. Validation ran from a temporary directory outside the checkout. Package import resolved from that environment, and both SDK and stdio MCP used isolated state with no ART-DEP-AI presence.

## Interface benchmark

Local Windows 11 / CPython 3.12.10 median milliseconds; direct and SDK use 20 samples, MCP uses 10. These are observations, not service-level thresholds.

| Operation | Direct service | SDK | MCP |
| --- | ---: | ---: | ---: |
| health | 0.0089 | 4.3996 | 10.4089 |
| recall | 1.4862 | 1.8038 | 6.3640 |
| cognition | 5.5593 | 5.8554 | 13.5214 |
| plan | 0.4362 | 1.1309 | 2.4124 |

The SDK overhead is mostly mapping/version metadata; MCP includes in-process protocol serialization/client dispatch. No threshold was specified and no semantic difference was observed.

## Limitations and decisions

SDK v1 is synchronous and limited-concurrency. Multi-process behavior remains the Phase 14 separate-connection model. Provider cancellation remains cooperative. Schemas are intentionally small, hand-maintained common-envelope schemas rather than generated per-operation schemas. Validation is Windows-only. Package 0.1.0 remains pre-1.0, and `LICENSE_DECISION_REQUIRED` still blocks public release. No ADR was created or modified because no architectural invariant changed.

## Exit checklist

- [x] Public API v1 and separate version
- [x] public facade and top-level lifecycle client
- [x] health/status, Study/source status, memory get, Recall, Cognition, Council, Planning
- [x] supervised execution exposure decision documented; no bypass
- [x] stable errors, retry semantics, deterministic serialization, typed IDs, provenance and epistemic semantics
- [x] version negotiation, handshake, capabilities, correlation propagation
- [x] host/SYUNE ownership and approval handoff documented
- [x] MCP v1, read/write classes, mode restrictions, error mapping, SDK parity
- [x] schemas/fixture, compatibility matrix, generic host, detachability/state-ownership proof
- [x] full regression and Phase 14 evals
- [x] final architecture check and diff check
- [x] interface benchmark and release-readiness update
- [x] ART-DEP-AI untouched; no migration; no Phase 17; no remote operation
- [x] local commit and clean working tree (verified after the enclosing commit)
