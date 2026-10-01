# Migration and upgrade policy

Durable product state schema is version 1. RC1 supports fresh state, same-version
restart, and the latest feature-frozen pre-RC Lean state. Run `syune upgrade check` before
deployment and back up the full state root.

There is no silent destructive migration. Newer schema, missing required stores, or
SQLite corruption must fail explicitly. Restore or perform a future documented migration;
never run `init` over damaged production state.
