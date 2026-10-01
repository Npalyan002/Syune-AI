# Host Integration Protocol v1

The host opens SYUNE, negotiates a version, checks health, discovers capabilities, invokes bounded operations, propagates one correlation ID through a task, and closes the runtime. The host never opens SYUNE database files or imports internal modules.

```text
User -> Host: explicit goal/context
Host -> SYUNE: handshake(["1"])
SYUNE -> Host: selected version, mode, health, capabilities
Host -> SYUNE: Study / Recall / Cognition / Council / Plan
SYUNE -> Host: typed results, provenance, gaps, risks, approval requirements
Host -> User: rendering and any approval presentation
```

## Ownership

| Concern | Owner |
| --- | --- |
| User identity | HOST |
| Host session and task | HOST |
| Canonical SYUNE memory | SYUNE |
| Study provenance | SYUNE |
| Planning artifacts | SYUNE |
| Approval presentation | HOST |
| Approval verification | SYUNE |
| External agent routing | HOST |
| External host tools | HOST |
| SYUNE capability execution | SYUNE |

The host owns interaction, orchestration, explicit goals, profile/Council selection, rendering, and host identity/context. SYUNE owns memory, provenance, Study, retrieval, cognition, profiles, Council, planning, governance, health, and the internal supervised execution boundary. SYUNE v1 has no global human identity or account model.

`HostContext` may carry host session ID, task ID, correlation ID, locale, timezone, explicit typed context references, host capability names, and whether an approval channel exists. These are routing/audit context, not memory identity. Correlation IDs should remain stable across Study -> Recall -> Cognition -> Council -> Plan. A generated ID is returned when one is omitted.

Capability discovery is authoritative for runtime mode. A host must not attempt unavailable operations. `READ_ONLY` and `SHADOW` omit writes. Planning is always proposal-only.

If a future public execution contract is activated, approval transport must bind the exact plan ID/version, exact proposal IDs and parameter hashes, risk/side-effect scope, budget, fingerprint, issuer, expiry, and revocation status. The host presents approval and SYUNE verifies it. Plaintext “yes”, self-issued approval, stale approval, parameter drift, and bypass flags are invalid. Public execution remains deferred in v1.

Errors use the public envelope. The host may retry only when `retryable=true`; unknown execution outcome is never a simple retry. Hosts ignore additive optional response fields, reject incompatible negotiated versions, enforce their own deadlines, and close on cancellation. SYUNE operations remain subject to internal hard limits and cooperative provider timing.

Generic agent pattern:

```text
User -> Host Orchestrator -> SYUNE Recall/Cognition -> Host decides next action
```

This protocol has no framework, cloud, REST, agent, or vendor dependency.
