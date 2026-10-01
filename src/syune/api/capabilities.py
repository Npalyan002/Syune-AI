"""Mode-aware public capability discovery."""
from .model import Capability, CapabilitySummary, RuntimeMode, SideEffectClass
from .version import PUBLIC_API_VERSION


def capability_summary(mode: RuntimeMode) -> CapabilitySummary:
    read = ("health", "status", "capabilities", "source_status", "memory_get", "recall", "context", "history", "audit")
    capabilities = [Capability(name, True, PUBLIC_API_VERSION, SideEffectClass.READ_ONLY, False, "LOCAL") for name in read]
    for name in ("cognize", "council", "plan"):
        capabilities.append(Capability(name, False, PUBLIC_API_VERSION, SideEffectClass.PLANNING_ONLY, False,
                                       "LOCAL", "research compatibility API; disabled in lean default"))
    writable = mode in (RuntimeMode.NORMAL, RuntimeMode.TEST)
    capabilities.append(Capability("study", writable, PUBLIC_API_VERSION, SideEffectClass.MEMORY_WRITE, False,
                                   "LOCAL", None if writable else "runtime mode is read-only"))
    capabilities.append(Capability("remember", writable, PUBLIC_API_VERSION, SideEffectClass.MEMORY_WRITE, False,
                                   "LOCAL", None if writable else "runtime mode is read-only"))
    capabilities.append(Capability("forget", writable, PUBLIC_API_VERSION, SideEffectClass.MEMORY_WRITE, False,
                                   "LOCAL", None if writable else "runtime mode is read-only"))
    capabilities.append(Capability("model", True, PUBLIC_API_VERSION, SideEffectClass.READ_ONLY, False,
                                   "CONFIGURED_PROVIDER", "requires an attached ModelGateway"))
    capabilities.append(Capability("execute_approved", False, PUBLIC_API_VERSION, SideEffectClass.SIDE_EFFECTING,
                                   True, "LOCAL", "deferred from public v1; Phase 13 host-bound API only"))
    return CapabilitySummary(mode, tuple(capabilities))
