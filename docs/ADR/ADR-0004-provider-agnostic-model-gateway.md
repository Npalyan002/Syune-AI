# ADR-0004 — Provider Agnostic Model Gateway

**Status:** Accepted  
**Applies to:** SYUNE v1

## Decision

Replaceable model providers sit behind ModelGateway and implement provider-independent request, result, policy, and failure contracts.

## Rationale

The public API must not inherit provider-specific transport, schema, retry, or failure behavior. Provider selection remains deployment policy.

## Consequences and boundaries

Adapters may translate transport details but cannot bypass authorization, budgets, structured validation, evidence sanitization, or semantic-commit idempotency. See [ModelGateway](../architecture/MODEL_GATEWAY.md).
