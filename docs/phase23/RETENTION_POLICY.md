# Retention policy

`RetentionPolicy` selects shared machinery by `MemoryClass`. Defaults archive/forget working memory after 7/30 days, episodes after 90/730 days, and semantic/entity/temporal memory on longer archive horizons. Procedural and organizational memory have no automatic expiry. Operators can replace every rule and set an active budget.

Protected records bypass automatic transitions. Explicit purge is never produced by decay. Superseded or invalidated records are archived during maintenance, preserving revision and audit evidence.
