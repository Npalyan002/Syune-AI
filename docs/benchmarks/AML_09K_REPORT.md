# AML-09K authorization partition performance repair

`AML_09K_STATUS = PASS`

AML-09K preserves the AML-09J authorization-first graph boundary and adds an
atomically published, generation-keyed authorization/BM25 partition cache. The
measured AML-09J bottleneck is materially reduced without changing retrieval
heuristics, model-free encoding, or security behavior. No production system,
registration, historical artifact, commit, tag, push, or release was changed.

## Profile-before-cache evidence

The uncached AML-09J profile separated the requested costs:

| Component | 3K median | 10K median |
|---|---:|---:|
| Authorization checks | 9.1 ms | 32.3 ms |
| Visible corpus construction | 11.4 ms | 42.2 ms |
| Authorized BM25 statistics/ranking | 17.0 ms | 42.8 ms |
| Semantic filter/over-fetch | 36.4 ms | 100.3 ms |
| Full recall | 219.3 ms | 238.5 ms |
| Repository get-all diagnostic | 1,438 ms | 3,650 ms |
| Sixteen index-locked lexical searches | 430.9 ms | 626.9 ms |

Visible corpus plus per-principal BM25 work was 85ms at 10K, roughly 36% of
full recall, justifying a combined partition/statistics cache. Semantic work was
also large but was deliberately not altered because changing candidate behavior was
outside this phase. A separate 512-edge profile measured endpoint authorization at
2.286ms and repository association access at 123.103ms.

After caching, a partition hit costs approximately 0.001–0.002ms. The 3K full-
recall microprofile improved from 219ms to 136ms and its sixteen-search index batch
from 431ms to 332ms. The 10K microprofile was noisy (315ms full recall) while its
cached BM25 component improved from 42.8ms to 23.3ms; Linux repetitions are the
capacity evidence of record.

## Cache publication and invalidation contract

Each `PolicyPartition` contains only IDs authorized for one immutable
`AccessContext`, aggregate document-token count, and per-term document frequency.
It is tagged with the index generation and published while holding the index lock.

The generation advances and all partitions are invalidated on every `sync`, `clear`,
and rebuild publication. Under the supported writer-preferring AML runtime, a writer
holds the write lock through durable mutation and index sync, then releases readers.
This covers Add, security/ownership replacement, lifecycle and temporal metadata,
association changes, recovery, and rebuilds. Association changes invalidate even
though they do not change corpus membership.

A generation mismatch fails closed. Per-request temporal and supersession checks
still run outside the cached authorization partition. Every admitted seed, both edge
endpoints, and every returned candidate are rechecked against the authoritative
repository. Direct service callers that mutate without the runtime lock retain the
final fail-closed check but are outside the supported atomic publication contract.

Aggregate hit/miss/invalidation counters are emitted only to private operational
logs. Privileged denial-audit events remain separate and no hidden ID, text, policy,
or denial telemetry is present in ordinary Search diagnostics or responses.

## Security and non-interference

Cold and warm tests verify that changing inaccessible records does not alter
candidate admission, BM25 corpus statistics/IDF, scores, ranking, fallback, returned
results, evidence status, or diagnostics. Other focused coverage includes direct and
source/context seeds, semantic crowd-out, multi-hop graph traversal, deny precedence,
shared names, lifecycle, ownership revocation, association publication, rebuild,
same-principal expansion, and concurrent Search/revocation under the runtime lock.

After a completed revocation and generation publication, no concurrent reader
observed the revoked seed or its graph neighbor. The original AML-09I exploit and
the complete AML-09J/K adversarial modules pass directly against packaged image
`sha256:962abbcb107366e08d6273ca6f0b9882b1386734d412a96ef05f34ab3e11dbd0`
with networking disabled and a read-only root.

Focused security/HTTP runs: 50 passed and 46 passed in the final targeted groups.
Container result: `container_adversarial=PASS files=2`.

## Frozen retrieval quality

No retrieval heuristic or scoring rule changed. Frozen results are bit-for-bit equal
to AML-09H and AML-09J:

| Metric | AML-09H/J | AML-09K |
|---|---:|---:|
| NFCorpus Recall@1/5/10/100 | .037362/.089272/.105626/.115816 | identical |
| NFCorpus MRR / nDCG / empty | .347436/.135754/.318885 | identical |
| SciFact Recall@5 / MRR / nDCG | .638167/.558670/.590495 | identical |
| SciFact empty rate | .020000 | identical |

The frozen 296-document, 392-query, 48-cluster synthetic gate remains Recall@5
1.0 with zero forbidden results. Model-free compliance remains intact.

## Repeated isolated Linux results

Environment and settings match AML-09J: WSL2 Ubuntu 24.04, Docker 29.1.3,
Compose 2.40.3, localhost TLS, disposable network/volume, dummy token, 2 CPU/2GiB
app limit, application concurrency 16, Uvicorn 40, Nginx 64r/s burst 64 with 40
connections, 16 Add plus 16 Search, and `top_k=100`.

The telemetry-corrected matrix contains three independent runs per size:

| Records | Throughput median (range) | Search p50 median (range) | p95 median | p99 median | Warm p99 median | CPU range | RSS range |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3K | 6.599 (6.591–7.532) rps | 4,378 (4,157–4,700) ms | 4,638 ms | 4,646 ms | 108 ms | 165.8–174.5% | 110–131 MiB |
| 10K | 5.797 (5.176–5.805) rps | 5,325 (5,225–5,695) ms | 5,432 ms | 5,440 ms | 287 ms | 162.9–177.3% | 153–159 MiB |

All six corrected runs returned 96/96 HTTP 200, with zero 429/503/5xx, cross-
principal rows, visibility failures, SQLite contention, or warm rebuilds. Every run
reported 102 cache hits, 5 misses, and 4 invalidations (95.3% hit rate). Recovery,
idempotent replay, 409 conflict behavior, and restart Search succeeded.

The preserved initial matrix had median throughput 7.655/5.806 rps at 3K/10K.
Its three 10K runs each had one error (one application 503 and two proxy 502), while
the corrected independent matrix had none. These remain disclosed as run-to-run and
capacity-tail risk rather than being discarded.

Compared with AML-09J's single runs, the corrected median improves throughput by
28% at 3K (5.143→6.599) and 24% at 10K (4.656→5.797); Search p99 improves 20%/21%
(5.82s→4.65s and 6.92s→5.44s). AML-09H remains faster at about 9.15 rps, so the
remaining semantic O(N) work and index serialization should be future optimization
targets, never at the expense of authorization.

## Regression, integrity, and decision

Complete suite: 481 passed, 2 failed, 2 warnings. The only failures are the known
historical v2.0.0 dependency-lock and dirty-candidate source-manifest checks;
historical artifacts remain unchanged. AML-09K candidate-only source, dependency,
test, profile, quality, and Linux evidence identities validate independently.

Security is mandatory and passed independently of quality and performance. The
measured bottleneck was materially reduced, quality is unchanged, the corrected
three-run Linux matrix is clean, and candidate integrity passes. AML-09K therefore
passes its local gate. A separate explicit authorization is still required before
any immutable commit, registration, or deployment.
