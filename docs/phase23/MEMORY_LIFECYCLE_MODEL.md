# Memory lifecycle model

`LifecycleState` has four operational states:

- `ACTIVE`: eligible for ordinary indexing and cognition.
- `ARCHIVED`: canonical and auditable, excluded from ordinary indexes, explicitly retrievable.
- `FORGOTTEN`: content remains canonical with a durable tombstone state, but is never cognitively eligible. Direct restoration is rejected.
- `PURGED`: canonical content and incident associations are physically deleted; lifecycle metadata and the audit event remain.

`TruthState` continues to describe epistemic status (`VERIFIED`, `SUPERSEDED`, `INVALIDATED`, etc.). Security remains in `SecurityEnvelope`; temporal validity remains in `TruthMetadata`. None is inferred from another.

All transitions append `LIFECYCLE` journal entries. Index rebuilds consult durable lifecycle rows, preventing resurrection.
