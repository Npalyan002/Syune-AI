# SQLite backup and restore

Stop every SYUNE process and copy the complete state root, including metadata, memory,
study, audit, and any remaining SQLite `-wal`/`-shm` files. Protect it as sensitive data.

Restore only while stopped: preserve the damaged root, place the complete backup at the
configured path, then run `syune upgrade check`, `syune health`, and authorized
retrieval/audit checks. Never merge database files from different times. RC1 has no
built-in hot-backup command; operators may use SQLite's online-backup API.
