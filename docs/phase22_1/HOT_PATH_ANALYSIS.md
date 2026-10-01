# Hot-path analysis

| Operation | Category | Before | After |
|---|---|---|---|
| Recall snapshot | QUERY_TIME | full materialization | REMOVED |
| Truth comparison | QUERY_TIME | all memories | BOUNDED by fact/context peers |
| Supersession | QUERY_TIME | global reconstruction | indexed lookup |
| Lexical candidates | QUERY_TIME | unbounded union/sort | planned and capped |
| Change discovery | SYNC_TIME | full scan | cursor journal |
| Health count | OBSERVABILITY_TIME | full scan | counter/SQL count |
| Rebuild | RECOVERY_TIME | full scan | UNCHANGED intentionally |

Twenty broad 100K queries: before 7.98M calls/5.098 s; after 15,921 calls/0.007 s.
