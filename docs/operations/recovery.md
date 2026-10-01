# ModelGateway recovery

ModelGateway persists enough state to recover logical calls across process termination. A restarted process either resumes from durable execution state or returns the existing committed result. It must not create a second semantic commit or repeat a caller-side effect.

Before transport starts, abandoned reservations can be released. If transport may have completed but no durable response exists, recovery records `REMOTE_COMPLETION_AMBIGUOUS`; automatic retry is disabled by default because the provider may already have performed the request. After result persistence or semantic commit, recovery reuses that durable state.

Request fingerprints use canonical encoding for dataclasses, enums, sets, and other unordered values so the same logical request remains stable across processes. Usage is reconciled before post-response failure points where possible; unknown ambiguous usage remains conservatively reserved.
