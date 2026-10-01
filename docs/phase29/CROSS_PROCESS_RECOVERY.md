# Cross-process recovery

Eight boundaries used real child-process termination (`os._exit(91)`) and fresh interpreter
restart. All 8 recovered to one semantic commit and one caller side effect. Pre-request reservation
was released when transport had not started. The response-before-persistence boundary was recorded
as `REMOTE_COMPLETION_AMBIGUOUS` and exposed one duplicate provider attempt. Post-commit and
post-checkpoint restarts returned the committed result without another provider call.

The first run exposed nondeterministic cross-process fingerprints caused by unordered frozenset
serialization. Canonical dataclass/enum/set encoding fixed it. Raw-response usage is reconciled
before the post-persistence crash hook; unknown ambiguous usage remains conservatively reserved.
`crash_v3/report.json` is the final passing evidence.
