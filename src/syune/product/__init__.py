"""Local product lifecycle without cognitive authority.

Product modules are intentionally imported explicitly so lightweight commands such as
``syune --version`` do not construct or import the runtime service graph.
"""
from .modes import LeanAssembly, LeanMode, context_only, full_lean, memory_context, memory_only, model_gateway_only

__all__ = ["LeanAssembly", "LeanMode", "context_only", "full_lean", "memory_context", "memory_only", "model_gateway_only"]
