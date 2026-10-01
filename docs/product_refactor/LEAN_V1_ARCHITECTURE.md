# Lean V1 architecture

```text
host -> SDK/MCP -> authorization -> retrieval -> context -> ModelGateway -> provider
                    |                 |
                    +-> memory <------+-> audit
                         |
                    provenance + temporal/version metadata + lifecycle
```

Context assembly is a bounded projection of governed recall. It does not infer truth: scores mean relevance, and stored observations remain observations. The ModelGateway is provider-neutral and handles structured output validation, budgets, retries, idempotency, fallback, evidence, and metrics.

Research packages have no dependency edge into the default runtime. Cognitive transactions are not invoked by recall or context.
