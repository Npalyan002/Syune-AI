# Tested Lean v1 examples

- `python -m syune.quickstart --state-root PATH` covers memory, governed context,
  provenance, revision/history, lifecycle, audit and restart using the installed package.
- `host_integration/host.py` demonstrates a generic host boundary.

Minimal agent flow:

```python
from syune import ContextRequest, Syune

with Syune.open(state_root="C:/syune-state", model_gateway=gateway) as runtime:
    context = runtime.context(ContextRequest("agent task", agent_id="agent-1", purpose="assist"))
    # Construct a ModelExecutionRequest whose user input includes context.data["rendered"].
    response = runtime.model(model_request)
```

The host owns the task and final response. SYUNE supplies governed context and reliable
model execution; it does not become an autonomous agent. ModelGateway construction is
provider-specific; deterministic gateway tests run without credentials.
