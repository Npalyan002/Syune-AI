"""Explicit detachable Lean v1 construction profiles."""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from syune.audit import SQLiteAuditStore
from syune.context import ContextService
from syune.memory import SQLiteMemoryRepository
from syune.retrieval import InvertedSeedIndex, RetrievalService

class LeanMode(str, Enum):
    MEMORY_ONLY="MEMORY_ONLY"; CONTEXT_ONLY="CONTEXT_ONLY"; MODEL_GATEWAY_ONLY="MODEL_GATEWAY_ONLY"
    MEMORY_CONTEXT="MEMORY_CONTEXT"; FULL_LEAN="FULL_LEAN"

@dataclass
class LeanAssembly:
    mode: LeanMode; memory: object=None; retrieval: object=None; context: object=None
    model_gateway: object=None; runtime: object=None; audit: object=None
    def health(self): return {"overall":"HEALTHY","mode":self.mode.value,"supported_operations":{
        LeanMode.MEMORY_ONLY:("remember","revise","history","lifecycle"),LeanMode.CONTEXT_ONLY:("context",),
        LeanMode.MODEL_GATEWAY_ONLY:("model",),LeanMode.MEMORY_CONTEXT:("remember","context","revise","history","lifecycle","audit"),
        LeanMode.FULL_LEAN:("remember","context","revise","history","lifecycle","audit","model")}[self.mode]}
    def close(self):
        if self.runtime is not None: self.runtime.close(); return
        if self.audit is not None: self.audit.close()
        if self.memory is not None and hasattr(self.memory,"close"): self.memory.close()
    def __enter__(self): return self
    def __exit__(self,*_): self.close()

def memory_only(path): return LeanAssembly(LeanMode.MEMORY_ONLY,SQLiteMemoryRepository(Path(path)))
def context_only(memory,*,audit=None):
    index=InvertedSeedIndex(memory); index.rebuild(); retrieval=RetrievalService(memory,index)
    return LeanAssembly(LeanMode.CONTEXT_ONLY,memory,retrieval,ContextService(memory,retrieval,audit),audit=audit)
def model_gateway_only(gateway):
    if not hasattr(gateway,"execute"): raise TypeError("model gateway must expose execute(request)")
    return LeanAssembly(LeanMode.MODEL_GATEWAY_ONLY,model_gateway=gateway)
def memory_context(root):
    root=Path(root); memory=SQLiteMemoryRepository(root/"memory.sqlite3"); audit=SQLiteAuditStore(root/"audit.sqlite3")
    value=context_only(memory,audit=audit); value.mode=LeanMode.MEMORY_CONTEXT; return value
def full_lean(*,state_root,model_gateway=None):
    from syune.product.config import load_config
    from syune.product.runtime import SyuneRuntime
    runtime=SyuneRuntime.open(load_config(cli_state_root=state_root))
    return LeanAssembly(LeanMode.FULL_LEAN,runtime.memory,runtime.retrieval,runtime.context,model_gateway,runtime,runtime.audit)

__all__=["LeanMode","LeanAssembly","memory_only","context_only","model_gateway_only","memory_context","full_lean"]
