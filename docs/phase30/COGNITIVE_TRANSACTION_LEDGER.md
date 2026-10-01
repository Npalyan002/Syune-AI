# Cognitive transaction ledger

The SQLite ledger records operation, subsystem, principal, purpose, authorized-context hash, gateway
logical/semantic identities, state, result, cost, and timestamps. `BEGIN IMMEDIATE`, primary/unique
constraints, and a process lock provide concurrent exactly-once application. Mutation and APPLIED
status share one transaction. Failure rolls both back, allowing a clean retry. APPLIED replay returns
the prior result without invoking the mutator.
