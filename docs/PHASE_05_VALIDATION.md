# SYUNE Phase 05 validation

**Result:** PASS after final gates, local commit, and clean-tree verification.

## Changes and dependency

Created `src/syune/gateway/mcp/{__init__,__main__,server}.py`, `tests/integration/test_mcp_gateway.py`, `tests/architecture/test_phase05_boundaries.py`, `scripts/benchmark_phase05.py`, `docs/PHASE_05_MCP_GATEWAY.md`, and this report. The user-supplied root `SYUNE_PHASE_05_MCP_GATEWAY.md` was preexisting untracked input and is committed unchanged. Modified `pyproject.toml`, `uv.lock`, `scripts/check_architecture.ps1`, and `src/syune/gateway/README.md`. No ADR created or modified. Direct runtime dependency: official `mcp>=2,<3`, resolved `mcp==2.2.0` (with `mcp-types==2.2.0`); transitive packages are SDK dependencies, not separately chosen web capabilities.

## Tests and protocol demonstrations

- Full `uv run pytest`: 84 passed.
- Static architecture check: PASS; exactly five allowlisted tools and no agent/Executive tool.
- Official SDK Client connected in process and over a real stdio subprocess; discovery found exactly the approved five tools.
- Health returned SYUNE, L1, ADVISORY, component status, and no state path.
- Memory get returned distinct typed Observation and Claim records with Source provenance; Recall returned typed candidates, decomposition, and provenance. Repeated Recall retained deterministic IDs/scores and left durable rows unchanged.
- Study of synthetic Markdown under the approved root returned NEW_SOURCE, ENCODED, MATERIALIZED; exact repeat returned ALREADY_STUDIED. Source bytes remained unchanged.
- Outside-root and traversal paths, plus unsupported extension, returned safe tool errors. No outside file was studied.
- Reopening both durable stores and rebuilding the index restored health, studied status, Observation lookup, and Recall.
- A synthetic missing MemoryTrace caused source status to report PARTIAL_MEMORY and Recall to return a safe degraded-materialization error.

## Local overhead baseline

`uv run python scripts/benchmark_phase05.py`: Windows 11 build 26200, Python 3.12.10, 20 in-process official MCP calls against a synthetic local source. Median total `syune_recall` call: **6.669 ms**; median RetrievalService: **5.686 ms**; median MCP/gateway overhead: **0.976 ms**. This is a local baseline with no release threshold and excludes stdio process startup.

## Decisions and exit checklist

No baseline deviation or blocking unresolved decision. Remote transport/authentication, public wire-schema commitments, and Phase 06 host integration remain deferred. No ART-DEP-AI modification or provider, agent, Control Core, Executive, arbitrary filesystem, shell, or web-fetch capability.

- [x] Official bounded MCP v2 dependency and explicit gateway package/factory.
- [x] Stdio and official SDK in-process sessions work; exactly five approved tools are discoverable.
- [x] Health, source status, typed memory get, associative recall, and explicit Study tools work.
- [x] Study roots and path escapes are enforced; source files stay read only; duplicate Study is idempotent.
- [x] Provenance, Observation/Claim distinction, and relevance-score meaning are preserved.
- [x] Restart over durable state and index rebuild works; lifecycle closes cleanly.
- [x] Structured safe errors and outputs; stdio stdout remains protocol-only; local latency measured.
- [x] No arbitrary filesystem/shell, agent-dispatch, Executive, Control Core, or ART-DEP-AI integration.
- [x] Full tests, architecture check, docs, local commit, clean tree, and no remote/push.
- [x] Phase 06 not started.
