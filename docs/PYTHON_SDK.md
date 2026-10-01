# Python SDK v1

Install the wheel and initialize a state root with `syune --state-root <absolute-path> init`. Configure allowed source directories with `SYUNE_STUDY_ROOTS` or `config.toml`. SDK v1 is synchronous, local, and in-process.

```python
from syune import CognitiveRequest, CouncilRequest, PlanRequest, RecallRequest, StudyRequest, Syune

with Syune.open(state_root=r"C:\state\syune") as brain:
    handshake = brain.handshake(["1"])
    health = brain.health(correlation_id="host-task-42")
    studied = brain.study(StudyRequest(r"C:\library\notes.md", "host-task-42"))
    recalled = brain.recall(RecallRequest(cue="release evidence", correlation_id="host-task-42"))
    cognition = brain.cognize(CognitiveRequest(cue="assess release evidence", correlation_id="host-task-42"))
    council = brain.council(CouncilRequest("assess release evidence", ("GENERAL", "RESEARCH"), correlation_id="host-task-42"))
    plan = brain.plan(PlanRequest("review the release evidence", correlation_id="host-task-42"))
```

`health`, `status`, `capabilities`, and `handshake` are read-only. `source_status`, `memory_get`, `recall`, `cognize`, and `council` are read-only cognitive operations. `plan` creates only in-memory planning artifacts. `study` is the sole v1 public memory write and is unavailable in `READ_ONLY` and `SHADOW` modes. `NORMAL` and `TEST` advertise it.

Use `TypedId.parse("ClaimId:<uuid>")` for memory references. `memory_get` returns a stable public record rather than a repository entity handle. All result objects contain `correlation_id`, `data`, and `public_api_version`. Diagnostics levels are `NONE`, `BASIC`, and `FULL`; FULL may expose scoring and structural reasoning records, never secrets or hidden chain-of-thought.

Catch `SyuneError` and branch on its stable `code` or `category`. `retryable` is explicit; callers must not infer retry safety from an exception class. Closing is idempotent. Prefer the context manager. A client owns one runtime graph and is limited-concurrency; create separate clients/connections for independently scheduled work and serialize writes to one state root.

There is no async client in v1. There is no `execute`, `execute_approved`, learning shortcut, repository accessor, DB accessor, reset, or implicit initialization API. Host applications present approvals, but public v1 does not transport them into execution.
