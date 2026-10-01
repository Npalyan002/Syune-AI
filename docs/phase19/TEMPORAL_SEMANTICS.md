# Temporal semantics

`observed_at` is when evidence was perceived. `recorded_at` is when SYUNE learned/stored its truth envelope. `valid_from` and `valid_until` are the half-open real-world validity interval. Missing values remain unknown.

`CURRENT` evaluates validity now and suppresses superseded/current-conflict losers. `HISTORICAL` evaluates `valid_at`. `AS_OF` evaluates real-world validity at `valid_at` while also excluding facts recorded after `knowledge_at`. Thus historical truth and knowledge available at the time remain distinct.

Ingestion order is not truth order; lineage and validity timestamps determine behavior. Late-arriving observations are covered by adversarial tests.
