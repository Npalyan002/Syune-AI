# Migration architecture

Authorized candidates and purpose constraints are resolved before `ModelExecutionRequest` creation.
The canonical sequence is:

`authorized context → ModelGateway → durable semantic commit → CognitiveTransactionLedger → atomic domain mutation → APPLIED`.

Gateway retries, repair and fallback never execute a cognitive mutator. A terminal gateway result
raises an explicit unavailable outcome and creates no transaction. The mutator shares the ledger
SQLite transaction, so multi-write changes and the APPLIED marker commit or roll back together.
Cross-database effects must use an existing idempotent domain API; no cross-database atomicity claim
is made.
