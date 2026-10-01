# Lean v1 threat model

| Threat | Mitigation | Residual risk |
|---|---|---|
| Unauthorized/cross-scope access | deny-first principal, purpose, scope checks | host identity and policy configuration |
| Provider exposure | provider/data-policy allowlists | provider and network behavior |
| Prompt/context injection | bounded provenance-bearing context | consuming models may follow hostile text |
| Secret persistence | recursive audit-key redaction | secrets in arbitrary text need upstream DLP |
| Audit tampering | separate durable correlated store | local admins can alter files; no cryptographic log |
| Storage theft | local-only default | encryption is operator-managed |
| Malformed provider output | schema/semantic validation and typed failures | validator correctness |
| Budget abuse | reservation, limits, reconciliation | operator policy sizing |
