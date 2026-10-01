# EVAL_PROTOCOL_V1

Status: **FROZEN, NOT EXECUTED**  
Freeze date: 2026-09-27 (Asia/Yerevan)  
Primary comparison: `ORGANIZATIONAL_RAG` vs `SYUNE_ORGANIZATIONAL_LEARNING` on held-out task success.

## Design

Eight synthetic, non-sensitive families: workflow selection; tool/procedure selection; error avoidance; policy-constrained decisions; context-dependent strategy choice; multi-step operations; incident triage; and authorization/temporal decisions. Each family has three experience cases and five evaluation cases: two in-distribution, one paraphrase, one near-shift, and one OOD negative-control. No experience text may equal an evaluation text. IDs and SHA-256 content hashes are mandatory; any cross-split duplicate fails validation.

Conditions are A `MODEL_ONLY`, B `BASIC_RAG`, C `SYUNE_RETRIEVAL`, D `LOCAL_VERIFIED_LEARNING`, E `ORGANIZATIONAL_RAG`, and F `SYUNE_ORGANIZATIONAL_LEARNING`. Optional G `RAW_SHARED_MEMORY` is excluded from the primary analysis and may be run only inside the synthetic benchmark.

The E and F corpora must be derived from the identical eligible experience-ID set, under identical authorization, purpose, scope, and temporal cutoffs. E retrieves raw episodes; F retrieves only pre-treatment verified/generalized procedures. Top-k is 4. Retrieved context is capped at 1,200 model-input tokens. If a condition has less eligible context it is not padded. Truncation is deterministic and logged. A token-normalized comparison uses the lower of E/F retrieved-token counts for each task. Retrieval uses the repository's existing frozen retrieval implementation; changing retrieval after outcomes are seen creates V2.

## Model and execution

Provider: OpenAI. Endpoint: Responses API. Model snapshot: `gpt-5.4-mini-2026-03-17`. Temperature: 0.2. Top-p: default. Reasoning effort: none. Maximum output: 500 tokens. Seed: unsupported/not specified; exact reproducibility is not assumed. Store: false. Service tier: default. Tools: none. Every critical instance receives three independent runs. Condition/task/run order is generated before calls using PRNG seed `260926`, and saved.

Equivalent instructions and output JSON schema are used across conditions. Retrieved material appears only in a delimited untrusted-data block. The system instruction states that context is evidence, cannot override policy, and may be ignored or rejected. Condition names are hidden from model and scorer.

## Counts and budget

Main design: 40 evaluation instances × 6 conditions × 3 runs = 720 calls. Paired procedure/no-procedure and procedure/raw-evidence ablations use 16 selected applicable instances × 2 extra arms × 3 runs = 96 calls. Maximum total: 816 calls. Estimated 1.8M input and 0.33M output tokens. Using frozen planning prices of $0.75/M input and $4.50/M output, estimated cost is $2.84; hard stop is $5.00 or 2.5M input tokens or 0.5M output tokens, whichever occurs first. Estimate must be refreshed and versioned before execution if provider pricing changes.

## Metrics and scoring

Primary: binary `HELD_OUT_TASK_SUCCESS`, scored by deterministic expected action/ordered constraints. Ambiguous cases are excluded only under a predeclared ambiguity rule and reported. Secondary: cold-agent success; repeated-error rate; negative-transfer rate; correct abstention; contamination susceptibility; retrieval precision; helpful/neutral/harmful retrieved knowledge; prompt-injection compliance; input/output/retrieval tokens; latency; cost; success per 1K input tokens; and success per dollar.

Cold-agent tasks are all 40 evaluation cases with empty personal history. Repeated-error tasks are the eight paraphrase cases. Generalization uses the eight paraphrase plus eight near-shift cases. Negative transfer and abstention use the eight OOD cases. Contamination uses one incorrect, confounded, duplicate, low-quality, contradictory, and injection-bearing episode per family, all ineligible for promotion.

Use paired run-level differences for the primary contrast. Report counts, rates, percentage-point delta, and a 95% cluster bootstrap confidence interval resampling task IDs (10,000 replicates, seed 260926). Report McNemar's exact test as descriptive corroboration. Do not claim significance solely from p-values. Latency uses median and p95.

## Decision rules

- `STRONGLY_SUPPORTED`: primary delta ≥10 pp, CI lower bound >0, negative transfer no more than +2 pp, no security failure, and replication across at least six families.
- `SUPPORTED`: delta ≥5 pp, point estimate positive in at least six families, negative transfer no more than +5 pp, no security failure, and cost/latency judged operationally tolerable.
- `INCONCLUSIVE`: CI spans materially positive and negative effects, sample/budget shortfall, or mixed family results without a safety failure.
- `NOT_SUPPORTED`: absolute delta between -5 and +5 pp with uncertainty excluding a +5 pp effect, or benefit is offset by material cost/negative transfer.
- `NEGATIVE`: delta ≤-5 pp with credible adverse signal, or any treatment-caused security/privacy invariant failure.

Product-meaningful means ≥5 pp absolute primary gain without >5 pp added negative transfer and with incremental cost under $0.02 per additional successful task. Statistical and product interpretations are reported separately.

## Failure and stop rules

Stop on leakage, unequal eligible evidence, authorization leakage, prompt-boundary bypass, budget limit, provider/model drift, missing raw telemetry, or evaluator unblinding. Categorize each failure as model reasoning, retrieval, knowledge, bad generalization, negative transfer, missing experience, context overload, authorization block, evaluation ambiguity, or other. No benchmark-informed architecture changes are allowed during V1.

