# Complexity profile

| Measure | STRONG_RAG | RAG_SYNTHESIS | PRODUCTION_SYUNE |
|---|---:|---:|---:|
| Persistent components | 2 | 2 | 6 |
| Model calls/task | 1 | 2 planned | 1 |
| Cognitive transaction | no | no | yes |
| Organizational maintenance | no | no | yes |

Measured SYUNE database writes were 3.92 per task. Its retained evidence, cognitive ledger,
memory, organizational-learning store and result evidence occupied 8,935,664 bytes across
the experiment, or 14,892.8 bytes per treatment task when allocated over all 600 units.
Epoch-boundary index rebuilds and 200 learning-maintenance operations were required.

The component ratio versus RAG_SYNTHESIS was 3.0 and the operational burden was classified
as high. Exercised failure modes included structured truncation, retry exhaustion, budget
exhaustion, remote ambiguity, semantic rejection, gateway replay, cognitive replay, stale
knowledge and revocation/demotion paths.
