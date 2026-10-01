# Legacy access policy

Legacy records without a security envelope use the explicit `LEGACY_LOCAL_COMPATIBLE` rule. Existing local callers retain compatibility by default. Enterprise/strict callers set `legacy_local_compatible=False`, causing unenveloped records to fail closed.

New secured records default to `SECURE_DENY`; absence of a principal is not an implicit allow. Legacy compatibility is never interpreted as global sharing and does not override a present security envelope.
