# Scope expansion policy

Every upward transition requires an exact `ScopeExpansionGrant` naming source kind, target scope, policy, actor, reason, task classes, purposes, and issue time. Project and department are sibling scopes; neither silently inherits from the other. Cross-organization promotion is rejected unconditionally.

Each successful evaluation writes `scope_expansion_audit` with source, target, policy, evidence IDs, actor, timestamp, and reason. Organization-wide promotion is never automatic. A grant does not bypass evidence, privacy, context, or policy-conflict checks.
