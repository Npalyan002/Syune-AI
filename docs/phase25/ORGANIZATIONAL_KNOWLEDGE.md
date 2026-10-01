# Organizational knowledge

`OrganizationalKnowledge` records the procedure, applicability, confidence, supporting and contradicting IDs, correlation-cluster count, scope, purpose, validity support time, revision, state, excluded private fields, and materialized procedure ID.

Supported scopes are `AGENT_PRIVATE`, `PROJECT`, `DEPARTMENT`, and `ORGANIZATION`. The materialized object is referenced from the shared memory repository; it is not copied into every agent store. Receiving agents retrieve it on demand through the existing authorized retrieval path.

Precedence is explicit: authoritative policy wins; otherwise valid, more-specific local knowledge may win when its evidence quality is at least organizational quality; invalid knowledge loses; unresolved cases abstain or use valid organizational knowledge.
