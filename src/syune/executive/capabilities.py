"""Fixed-purpose adapters confined to a caller-provided SYUNE sandbox root."""
from pathlib import Path
from .errors import ExecutionError,ExecutionErrorCode
from .runtime_model import *
class RetryableCapabilityError(Exception):pass
class UnknownCapabilityOutcome(Exception):pass
class CapabilityRegistry:
    def __init__(self):self._entries={}
    def register(self,descriptor,adapter):
        if descriptor.id in self._entries:raise ValueError("duplicate capability ID")
        if not set(descriptor.input_fields):raise ValueError("input schema required")
        self._entries[descriptor.id]=(descriptor,adapter)
    def resolve(self,capability_id):
        if capability_id not in self._entries:raise ExecutionError(ExecutionErrorCode.CAPABILITY_NOT_FOUND,"capability not registered")
        return self._entries[capability_id]
    def descriptors(self):return tuple(x[0] for x in sorted(self._entries.values(),key=lambda x:str(x[0].id)))
class LocalSandboxFileAdapter:
    """Creates/updates/deletes one relative file under a fixed sandbox; no shell or network."""
    def __init__(self,root,max_file_bytes=1_000_000,max_storage_bytes=10_000_000):
        if not 0<max_file_bytes<=1_000_000 or not max_file_bytes<=max_storage_bytes<=10_000_000:raise ValueError("sandbox bounds exceeded")
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True);self.calls=0;self._before={}
        self.max_file_bytes=max_file_bytes;self.max_storage_bytes=max_storage_bytes
    def _path(self,params):
        value=dict(params).get("path","")
        if Path(value).is_absolute() or ".." in Path(value).parts or ":" in value:raise ValueError("relative sandbox path required")
        target=(self.root/value).resolve()
        if not value or target==self.root or self.root not in target.parents:raise ValueError("target outside execution sandbox")
        return target
    def invoke(self,invocation):
        self.calls+=1;p=dict(invocation.parameters);target=self._path(invocation.parameters);mode=p.get("mode","")
        existed=target.exists()
        size=len(p.get("content","").encode("utf-8"))
        if size>self.max_file_bytes or (existed and target.stat().st_size>self.max_file_bytes):raise ValueError("sandbox file byte limit")
        used=sum(x.stat().st_size for x in self.root.rglob("*") if x.is_file())
        if used+size>self.max_storage_bytes:raise ValueError("sandbox storage byte limit")
        self._before[invocation.idempotency_key]=(target,existed,target.read_bytes() if existed else None)
        if mode=="retryable" and self.calls==1:raise RetryableCapabilityError("synthetic retryable failure")
        if mode=="unknown":
            target.parent.mkdir(parents=True,exist_ok=True);target.write_text(p.get("content",""),encoding="utf-8");raise UnknownCapabilityOutcome("effect may have occurred")
        target.parent.mkdir(parents=True,exist_ok=True)
        if p.get("operation","write") == "delete":
            if target.exists():target.unlink()
        else:target.write_text(p.get("content",""),encoding="utf-8")
        return (("path",str(target.relative_to(self.root))),("content",p.get("content","")),("operation",p.get("operation","write")),("mode",mode))
    def verify(self,invocation,raw):
        p=dict(invocation.parameters);target=self._path(invocation.parameters)
        if p.get("mode")=="verify_fail":return False,"forced mismatch"
        if p.get("operation","write")=="delete":return not target.exists(),"absent" if not target.exists() else "present"
        observed=target.read_text(encoding="utf-8") if target.exists() else "<missing>";return observed==p.get("content",""),observed
    def rollback(self,invocation):
        target,existed,data=self._before[invocation.idempotency_key]
        if self._path(invocation.parameters)!=target:raise ValueError("rollback target drift")
        if existed:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        elif target.exists():target.unlink()
        return self.verify_rollback(invocation,existed,data)
    def verify_rollback(self,invocation,existed,data):
        target=self._path(invocation.parameters);ok=target.exists()==existed and (not existed or target.read_bytes()==data);return ok,"restored" if ok else "rollback mismatch"
