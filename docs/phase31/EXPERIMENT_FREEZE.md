# Phase 31 executable freeze

The final experiment uses 200 paired provider-facing tasks per treatment: twenty task
families, five departments and ten ordered epochs. One task per family and epoch is the
smallest sample that preserves every required longitudinal trajectory and replacement cohort.

The three treatments are `STRONG_RAG`, `RAG_SYNTHESIS`, and `PRODUCTION_SYUNE`. There are
600 decision calls and 200 planned synthesis calls. The exact model is
`gpt-5.4-mini-2026-03-17`, temperature 0.2. The estimated provider cost was $1.776 with a
$5.00 hard cap. Dataset, ground truth, preregistration and content hashes are saved under
`evidence/live_v1/freeze/`.

Ground truth is stored separately and enters only outcome revelation and blinded scoring.
It is rejected by the provider prompt builder. The live runner uses production ModelGateway;
SYUNE also uses production memory, authorization, retrieval, organizational learning and the
cognitive transaction ledger.

The complete fake-provider traversal executed 600 tasks and 800 gateway calls before live
treatment. It found and resolved two pre-freeze integration defects: accidental epoch-name
partitioning of hypotheses and missing simulation-time retrieval context.
