# SYUNE `2.0.0-aml-r2` candidate package

This package describes the reviewed, uncommitted AML-09A through AML-09M candidate.
It does not modify the immutable v2.0.0 release, an AML registration, or production.

- Baseline: `23d76717feff156849acc5e6b66aac088cd92afb`
- Candidate: `2.0.0-aml-r2`
- Division/track: Open-source Methods / Textual Memory
- Encoding: deterministic and model-free
- Generative LLM: N/A
- Embedding model: N/A
- Frozen image: `sha256:962abbcb107366e08d6273ca6f0b9882b1386734d412a96ef05f34ab3e11dbd0`

`commit-inventory.txt` is the exact selective source proposal. `SOURCE_DIFF.patch`
contains its tracked changes and new-file patches against the baseline.
`source-manifest.sha256` authenticates every proposed source file. `dependencies.txt`
records the frozen runtime dependencies. `aml09m-evidence-manifest.sha256`
authenticates the raw HTTP evidence under `docs/benchmarks/aml09m/`.

The AML-09M confirmation used three isolated 10K, 16 Add/16 Search runs. All 288
mixed-workload requests returned HTTP 200. New Nginx 502 responses were restricted
to `/health` during intentional application restarts and correlate with graceful
Uvicorn shutdown/startup. Historical AML-09K 502 responses cannot be attributed
with the same confidence because their error logs were not retained.

Historical v2.0.0 manifests remain unchanged. Their two expected dirty-candidate
test failures are disclosed rather than hidden by rewriting historical identities.
No commit, registration, official evaluation, release, or deployment is included.
