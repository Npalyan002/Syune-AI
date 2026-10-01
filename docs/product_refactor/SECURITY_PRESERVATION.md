# Security preservation

Authorization remains fail-closed for secured memory. Context assembly consumes already-authorized recall candidates and does not re-query around policy. Denied records are absent, not redacted placeholders. Access decisions remain queryable through `audit()`.

Direct `remember` writes can carry an owner and explicit principals. Plain text is stored as an `Observation`, not a verified fact. Temporal and truth metadata are surfaced as metadata, never converted to truth probability. Forgetting uses the lifecycle state and retrieval excludes forgotten content.
