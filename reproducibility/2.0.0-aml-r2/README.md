# SYUNE `2.0.0-aml-r2` canonical release metadata

This package identifies the reviewed AML-R2 implementation without changing its
runtime bytes.

- Baseline: `23d76717feff156849acc5e6b66aac088cd92afb`
- Immutable implementation commit: `845ef9630435a63c3cc277c6bb27283f6b34906e`
- Immutable implementation tree: `a6d6f3584769fc9b16bf27e7db2008675ffa8301`
- Corrective release commit: the Git commit containing this metadata
- Canonical byte source: Git blob bytes from the implementation commit
- Hash algorithm: SHA-256
- Candidate: `2.0.0-aml-r2`
- Encoding: deterministic and model-free
- Generative LLM: N/A
- Embedding model: N/A

`source-manifest.sha256` and `aml09k-source-manifest.sha256` hash immutable Git
blob content materialized with LF line endings. `candidate-manifest.toml` records
the acyclic manifest roots. The release-gate manifests depend on the candidate
manifest. `immutable-source-attestation.toml` is the final leaf and is not hashed
by any upstream manifest.

`SOURCE_DIFF.patch`, `commit-inventory.txt`, `dependencies.txt`, and the evidence
manifest remain artifacts of implementation commit `845ef963...`; their canonical
hashes are of the committed Git bytes. Raw benchmark evidence remains separately
checksummed and is not added to the source commit.

The historical v2.0.0 manifests and tag are unchanged. The older
`deploy/aml/source-change-manifest.sha256` is baseline-era metadata and is not an
R2 source-integrity root.

The correction changes release metadata only. It does not change executable
source, tests, dependencies, Dockerfile instructions, Compose behavior, retrieval,
authorization, concurrency, persistence, model-free encoding, or AML contracts.
