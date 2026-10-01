# Lean v1 examples

These examples use stable Lean v1 APIs only. They do not initialize experimental
cognition, learning, Council, Planner, or Executive services.

Install the package and initialize a separate state directory for each memory example:

```console
pip install syune
syune init --state-root .example-state
python examples/memory.py --state-root .example-state
```

| Example | Demonstrates |
|---|---|
| [`memory.py`](memory.py) | Remember, governed retrieval, full provenance, and restart |
| [`governed_context.py`](governed_context.py) | Owner-scoped memory, agent identity, purpose, bounded context, and denial |
| [`revision_history.py`](revision_history.py) | Revision, `CURRENT`, `AS_OF`, history, and lineage |
| [`model_gateway.py`](model_gateway.py) | Provider-neutral structured output with a deterministic local adapter and no credentials |
| [`agent_integration.py`](agent_integration.py) | Generic agent task → governed context → chosen model flow |

`host_integration/host.py` preserves the generic host-boundary compatibility example using
the same stable Lean flow and top-level imports only.

Every program is runnable without a live provider. The ModelGateway example uses a small
deterministic adapter to expose gateway concepts; replace it with an explicitly configured
provider adapter in production. Never embed provider credentials in source files.
