# Migration

The truth envelope has schema version `2`; the existing entity/table schema remains version `1` because storage is JSON and the change is additive. Old payloads decode using the envelope default: `OBSERVED`, all temporal/identity fields unknown, no inferred verification.

No rows are rewritten or destroyed. New writes persist the envelope. A restart reconstructs identical eligibility, lineage, contradiction, and audit semantics. Legacy records remain usable under `ALLOW_UNVERIFIED` and `PREFER_VERIFIED`; `VERIFIED_ONLY` excludes them.
