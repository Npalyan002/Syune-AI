# AML-09M release blocker closure

`AML_09M_STATUS = READY_FOR_COMMIT`

This phase changed release metadata and generated evidence only. Retrieval,
authorization, runtime behavior, the frozen image, historical v2.0.0 manifests,
production, and AML registration were not changed.

## Reconciled candidate

- Baseline: `23d76717feff156849acc5e6b66aac088cd92afb`.
- Image: `sha256:962abbcb107366e08d6273ca6f0b9882b1386734d412a96ef05f34ab3e11dbd0`,
  89,682,249 bytes. No rebuild was performed.
- Selective inventory: 45 reviewed source, test, deployment, documentation, and reproducibility
  tooling files; bulk raw results are excluded from the commit proposal.
- Source patch SHA-256:
  `9445aec1b5873153a049b48aa2e8cd3c2785f5e56cebdcb26130c5156ea06724`.
- Source manifest SHA-256:
  `2a7c904a2b42671ae747f599459de10dd9ad4c285651d40ca19896ded8ac1f89`.
- Commit inventory SHA-256:
  `d3b30c02f1eb0a756847ef44469610b55db05394e05fa4f71ddd890acb0a4f4c`.
- Evidence manifest SHA-256:
  `c2222168150eada433239132022e682d799e34aa04f9217e5d3be9a5e8e873d5`.
- `uv.lock`: `7f06cfd0269d4f2ff68e53815925525270066e73c3f0fcfacc09f95feed4ecb8`.
- `pyproject.toml`:
  `8b19980152eb44011183aab49b44470b797cac8a4f92d2759639f9b22bfdb836`.

## Instrumented 10K confirmation

WSL2 Ubuntu 24.04, Docker 29.1.3, Compose 2.40.3, localhost TLS, disposable
network/volume, dummy bearer token, 2 CPU/2 GiB application limit, application
concurrency 16, Uvicorn 40, Nginx 64r/s burst 64 and 40 connections, three bursts
of 16 Add plus 16 Search, `top_k=100`.

| Run | Mixed HTTP | Throughput | Search p50/p95/p99 | Warm p99 | Queue p99 | CPU | Peak RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 96 x 200 | 5.798 rps | 5344/5591/5604 ms | 319 ms | 195 ms | 179.70% | 161.4 MiB |
| 2 | 96 x 200 | 5.167 rps | 5780/5888/5896 ms | 317 ms | 238 ms | 174.08% | 158.5 MiB |
| 3 | 96 x 200 | 5.795 rps | 5316/5650/5671 ms | 316 ms | 215 ms | 178.72% | 160.5 MiB |

All 288 mixed Add/Search requests returned 200. There were zero workload 409, 429,
502, 503, other 5xx, transport failures, visibility failures, cross-user rows,
SQLite contention events, or warm Search rebuilds. Each run separately verified the
expected global request-ID 409, idempotent 200 replay, and successful restart
recovery.

Nginx recorded 11/12/12 HTTP 502 responses, all for harness `/health` probes during
the intentional application restart. Timestamps correlate with graceful Uvicorn
shutdown, Docker `die` with exit code 0, the requested `restart` event, connection
refusal while the upstream was stopped, and successful Uvicorn startup. No `/add`
or `/search` request received 502. Health probes are excluded from workload success.

The historical AML-09K 502 events remain unattributed: their Nginx error logs and
failed response bodies were not retained. The new evidence demonstrates that the
approved configuration completes three equivalent workloads without an operational
failure, but does not retroactively prove that historical failures had the same
restart cause. Residual intermittent tail risk remains an operations/monitoring
concern rather than a source-commit blocker.

## Integrity and regression

The fresh AML-09L complete suite produced 481 passed, two historical-manifest
failures, and three warnings. Both failures compare the dirty R2 tree against
immutable v2.0.0 identities. Historical files were not changed; candidate-specific
manifests validate independently. AML-09I/J/K security, non-interference, concurrent
revocation, cache invalidation, quality, and packaged-image results remain frozen.

The exact commit proposal is `reproducibility/2.0.0-aml-r2/commit-inventory.txt`
plus the reconciled candidate metadata, this report, and the AML-09M release gate.
Raw logs and JSON under `docs/benchmarks/aml09m/` remain a separately checksummed
evidence package and are not proposed for the source commit.

An immutable commit is recommended only after explicit user authorization. No
commit, push, tag, release, deployment, registration, or official evaluation was
performed.
