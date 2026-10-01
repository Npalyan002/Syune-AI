# Historical evaluation summary

SYUNE development included phased reliability, retrieval, security, provider and product
evaluations. The public main branch retains the final human-readable validation reports,
release gates, benchmark source that remains reproducible, and the stable Lean v1 test
suite. Raw provider calls, runtime databases, treatment stores, repeated manifests and
intermediate generated output are intentionally excluded from the public tree.

The canonical product evidence is:

- `docs/lean_v1_validation/FINAL_REPORT.md`
- `docs/lean_v1_blocker_closure/FINAL_REPORT.md`
- `docs/release/RC_VALIDATION.md`
- `docs/release/v1.0.0.md`
- `benchmarks/lean_product.py`
- `benchmarks/lean_v1_quality_gate.py`
- `benchmarks/lean_v1_release_gate.py`

Historical raw evidence remains recoverable from Git history and the immutable
`syune-full-cognitive-pre-lean`, `v1.0.0-rc1`, and `v1.0.0` tags. Those artifacts are not
required to build, install, test or operate the Lean v1 product.
