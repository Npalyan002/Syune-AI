# SYUNE AML Deployment Runbook

This package prepares the Textual Memory adapter for deployment but does not
deploy it. The historical `v1.1.0` tag is only the baseline. Phase 02A through
04A are uncommitted working-tree changes and must never be represented as that
tag.

## Architecture

Run exactly one application process with one Uvicorn worker. Its bounded pool
permits four SDK operations and queues for one second; Uvicorn admits at most
eight connections. Every SDK operation owns its SQLite connections. The sole
state volume is an evaluation-only, ownership-marked root such as
`/var/lib/syune-aml`. Never mount personal or development SYUNE state.

Terminate TLS at Nginx. Only `/health`, `/add`, and `/search` are public. The
internal `/ready` endpoint remains on loopback/the container network and is not
routed by Nginx. Nginx enforces a 1 MiB body limit, eight requests/second per
source with a burst of sixteen, eight concurrent connections per source, and
`Retry-After: 1` on 429/503. Add/Search upstream and graceful-shutdown timeouts
are 1,800 seconds, matching the official maximum request duration. A production
load balancer may add a global limit, but must not shorten the 1,800-second
request deadline.

The container option is `deploy/aml/compose.yaml`. The VM option uses
`deploy/aml/syune-aml.service` behind the same Nginx policy. Both keep one
application process and use supervisor restart-on-failure behavior.

## Preflight and startup

1. Provision a private volume owned only by the service identity, with mode
   `0700`, at the configured absolute state root. Allow at least 1 GiB free
   above the declared evaluation capacity.
2. Put the bearer token and TLS private key in the platform secret manager.
   Materialize them as files readable only by the service identity. Never put
   values in an environment file, image, command line, log, or repository.
3. Review `deployment-manifest.toml`. Before production, create an approved
   immutable source revision for these changes. The supplied container references
   already include Docker Hub OCI-index digests; verify them again at promotion. Record the source revision, image
   digests, lock hash, config hash, build timestamp, and operator approval.
4. Verify `sha256sum uv.lock` equals the manifest. Run `uv sync --frozen
   --no-dev`; do not regenerate the lock during deployment.
5. For a local VM simulation, set the non-secret variables from
   `environment.example`, set `SYUNE_AML_BEARER_TOKEN_FILE` to an absolute
   private test file, then run:

       uv run --frozen uvicorn syune.adapters.aml.v1:app_from_environment \
         --factory --host 127.0.0.1 --port 8080 --workers 1 \
         --limit-concurrency 8 --timeout-graceful-shutdown 1800 \
         --no-access-log --no-server-header

6. Require `GET /health` to return `{"status":"ok"}` and the internal
   `GET /ready` to return `{"status":"ready"}` before admitting traffic.
   A readiness failure is intentionally generic and means configuration,
   marker, writable-volume, disk-floor, capacity, or SQLite checks failed.

## Security and monitoring

Use TLS 1.2 or 1.3 with a trusted certificate and rotate secrets through the
secret manager. Keep interactive documentation and debug endpoints disabled.
The application and proxy structured logs contain only time, method, route,
status, response size, and duration; they omit bodies, query strings,
identifiers, authorization headers, and secrets. Restrict log access and set a
retention policy no longer than operational need.

Alert on readiness failure, restart loops, sustained 429/503/5xx responses,
p95/p99 latency, disk free space, database/WAL growth, open-file use, CPU, and
memory. Do not attach request or response payloads to alerts. Run application
containers without root, capabilities, a writable root filesystem, or access
to host/developer directories.

SQLite is a single-writer store. Do not scale the application horizontally or
increase workers. Search may overlap reads, but ingestion is serialized by the
database. Keep `max_concurrency=4` and server connection limit 8 until measured
with production-equivalent storage. On lock contention, return a sanitized
failure and let the AML caller retry the same `request_id`; do not bypass
idempotency.

## Capacity declaration

Complete and approve this record before launch:

    Source revision: <immutable revision, not v1.1.0>
    Application base image: python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
    Proxy image: nginx:1.28.0-alpine@sha256:30f1c0d78e0ad60901648be663a710bdadf19e4c10ac6782c235200619158284
    Python / uv.lock SHA-256: <versions and hash>
    Volume class / provisioned GiB / free GiB: <values>
    Expected Add requests / messages / bytes: <values>
    Expected Search requests / top_k / concurrency: <values>
    max_concurrency / connection limit / rate and burst: 4 / 8 / 8r/s, 16
    Peak RSS and disk growth from rehearsal: <values>
    30-minute request test result: <value>
    Snapshot method, encryption, region, retention: <values>
    Owner, on-call, launch and deletion dates: <values>

## Safe restart and rollback

Stop admission at the proxy, wait for active requests (up to 1,800 seconds),
send SIGTERM, and allow the configured 1,860-second supervisor stop window.
After restart, require readiness and replay uncertain Adds with their original
request IDs. Never kill the process merely because an Add response is slow.

Before an upgrade, stop writes and take an encrypted, application-consistent
snapshot of the entire marked state root. Roll back code/config to the last
approved immutable image and restore the matching whole-root snapshot only if
schema compatibility requires it. Never copy individual SQLite/WAL files from
a live volume. Verify marker, permissions, readiness, replay idempotency, and a
synthetic isolated user search before reopening traffic.

## Retention and cleanup

The evaluation data policy remains deletion within 30 days after the evaluation
ends. The operator must first confirm the organizer's end date and inventory
the live volume, audit/idempotency/session data, temp files, logs, monitoring
exports, encrypted snapshots, backups, and any provider copies.

No automatic destructive schedule is installed by this package.

After stopping the service and expiring required recovery copies, run
`deploy/aml/cleanup_evaluation.py` with both the absolute root and the identical
resolved `--confirm-root`. The cleanup refuses symlinks, broad paths, and roots
without the AML ownership marker. Delete external logs, snapshots, backups, and
provider replicas through their native controls, record evidence and dates,
then verify the state root and external copies no longer exist. This procedure
must never target development or personal state.
