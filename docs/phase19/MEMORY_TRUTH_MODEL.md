# Memory truth model

The version-2 `TruthMetadata` envelope defines `OBSERVED`, `ASSERTED`, `SUPPORTED`, `VERIFIED`, `DISPUTED`, `SUPERSEDED`, and `INVALIDATED`. Allowed transitions are executable in `memory.truth.ALLOWED_TRANSITIONS`; terminal invalid/superseded states cannot transition.

`VERIFIED` means evidence/process has verified the item, not eternal truth. `DISPUTED` remains traceable. `INVALIDATED` is never retrieval-eligible. Current retrieval excludes explicit and reverse-lineage superseded items. Legacy entities default to `OBSERVED` with unknown times and are never upgraded to verified.

Material changes are reconstructed as `memory_verified`, `memory_disputed`, `memory_superseded`, `memory_invalidated`, and `contradiction_detected` events through `truth_events()`.
