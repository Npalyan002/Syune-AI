# Startup metrics

Structural before/after measurement:

| Metric | Full default | Lean default |
|---|---:|---:|
| Open SQLite repositories | 4 | 2 |
| Constructed domain services/indexes | 11 | 5 |
| Research services constructed | 4 | 0 |
| Learning coupled to recall | yes | no |
| Context service | no | yes |

The full values are derived from the tagged `SyuneRuntime.open`; lean values are asserted by `tests/lean/test_lean_product.py`. Wall-clock startup varies by machine and corpus because index rebuild is data-dependent, so no universal latency claim is made.
