# Audit chain

The end-to-end join is:

`principal + purpose + authorized_context_hash → operation_key → gateway_logical_call_id → provider attempts → gateway_semantic_commit_id → cognitive_transaction_id → result/effect`.

The cognitive ledger indexes the gateway logical call and records subsystem, cost, state and
timestamps. Provider evidence stays in the Phase 29 store. Raw authorized context is not duplicated
into the cognitive ledger, preserving least-retention behavior while retaining verifiable lineage.
