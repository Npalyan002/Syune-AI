"""Network adapters for production embedding and ANN services."""
from __future__ import annotations

import json
from typing import Callable, Mapping
from urllib import error, parse, request

from syune.core import ClaimId, ConceptId, EpisodeId, EvidenceId, MemoryTraceId, ObservationId, ProcedureId, SourceId
from syune.memory.model import NodeId
from syune.retrieval.hybrid import (BackendHealth, EmbeddingIdentity, EmbeddingSpaceMismatch,
    EmbeddingUnavailable, VectorIndexStats, VectorIndexUnavailable)

_ID_TYPES = {kind.__name__: kind for kind in (SourceId, ObservationId, ConceptId, ClaimId, EvidenceId, EpisodeId, ProcedureId, MemoryTraceId)}


class OpenAICompatibleEmbeddingProvider:
    """Batch adapter for OpenAI-compatible ``/v1/embeddings`` APIs."""
    def __init__(self, *, base_url: str, api_key: str, model: str, dimensions: int,
                 model_version: str = "provider-managed", timeout_seconds: float = 30,
                 configuration: str = "default", transport: Callable[[request.Request, float], bytes] | None = None):
        if not base_url.startswith(("http://", "https://")) or not api_key or not model or dimensions < 1:
            raise ValueError("base_url, api_key, model, and positive dimensions are required")
        self.base_url, self.api_key, self.model = base_url.rstrip("/"), api_key, model
        self.dimensions, self.version, self.timeout_seconds = dimensions, model_version, timeout_seconds
        self.identity = EmbeddingIdentity("openai-compatible", model, model_version, dimensions, configuration)
        self._transport = transport or self._send
    @staticmethod
    def _send(req, timeout):
        with request.urlopen(req, timeout=timeout) as response: return response.read()
    def embed(self, texts):
        if not texts: return ()
        req = request.Request(f"{self.base_url}/v1/embeddings",
            data=json.dumps({"model":self.model,"input":list(texts),"dimensions":self.dimensions}).encode(), method="POST",
            headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"})
        try:
            body=json.loads(self._transport(req,self.timeout_seconds)); ordered=sorted(body["data"],key=lambda x:x["index"])
            vectors=tuple(tuple(float(v) for v in item["embedding"]) for item in ordered)
            if len(vectors)!=len(texts) or any(len(v)!=self.dimensions for v in vectors):
                raise EmbeddingSpaceMismatch("provider returned an unexpected batch size or dimension")
            return vectors
        except EmbeddingSpaceMismatch: raise
        except (error.URLError,TimeoutError,OSError,KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:
            raise EmbeddingUnavailable(f"embedding provider unavailable: {type(exc).__name__}") from exc


class QdrantVectorIndex:
    """Production-capable Qdrant HNSW adapter using its HTTP API."""
    version="qdrant-http-v1"
    def __init__(self, *, base_url: str, collection: str, api_key: str|None=None, timeout_seconds: float=10,
                 transport: Callable[[request.Request,float],bytes]|None=None):
        if not base_url.startswith(("http://","https://")) or not collection: raise ValueError("Qdrant base_url and collection are required")
        self.base_url,self.collection,self.api_key=base_url.rstrip("/"),collection,api_key
        self.timeout_seconds,self._transport=timeout_seconds,transport or self._send
        self.embedding_space_id=None; self.dimensions=0
    @staticmethod
    def _send(req,timeout):
        with request.urlopen(req,timeout=timeout) as response: return response.read()
    def _call(self,method,suffix="",body=None):
        headers={"Content-Type":"application/json"}
        if self.api_key: headers["api-key"]=self.api_key
        req=request.Request(f"{self.base_url}/collections/{parse.quote(self.collection)}{suffix}",
            data=None if body is None else json.dumps(body).encode(),method=method,headers=headers)
        try: return json.loads(self._transport(req,self.timeout_seconds) or b"{}")
        except (error.URLError,TimeoutError,OSError,ValueError,json.JSONDecodeError) as exc:
            raise VectorIndexUnavailable(f"Qdrant unavailable: {type(exc).__name__}") from exc
    def configure(self,identity):
        result=self._call("GET").get("result",{}); size=result.get("config",{}).get("params",{}).get("vectors",{}).get("size")
        if size is not None and int(size)!=identity.dimensions: raise EmbeddingSpaceMismatch("Qdrant dimension mismatch; rebuild required")
        points=self._call("POST","/points/scroll",{"limit":1,"with_payload":True,"with_vector":False}).get("result",{}).get("points",[])
        space=points[0].get("payload",{}).get("embedding_space") if points else None
        if space is not None and space!=identity.space_id: raise EmbeddingSpaceMismatch("Qdrant embedding space mismatch; rebuild required")
        self.embedding_space_id,self.dimensions=identity.space_id,identity.dimensions
    def create_collection(self,identity):
        self._call("PUT","",{"vectors":{"size":identity.dimensions,"distance":"Cosine"},"on_disk_payload":True})
        self.embedding_space_id,self.dimensions=identity.space_id,identity.dimensions
    def upsert(self,memory_id,vector,metadata=None): self.upsert_many(((memory_id,vector,metadata or {}),))
    def upsert_many(self,items):
        if not self.embedding_space_id: raise EmbeddingSpaceMismatch("configure index before writes")
        points=[]
        for mid,vector,metadata in items:
            if len(vector)!=self.dimensions: raise EmbeddingSpaceMismatch("vector dimension mismatch")
            payload={"memory_id":str(mid),"memory_type":type(mid).__name__,"embedding_space":self.embedding_space_id,**dict(metadata)}
            points.append({"id":str(mid),"vector":list(vector),"payload":payload})
        if points: self._call("PUT","/points?wait=true",{"points":points})
    def remove(self,memory_id): self._call("POST","/points/delete?wait=true",{"points":[str(memory_id)]})
    def search(self,vector,limit,metadata_filter=None):
        if len(vector)!=self.dimensions: raise EmbeddingSpaceMismatch("query dimension mismatch")
        must=[{"key":"embedding_space","match":{"value":self.embedding_space_id}}]
        must.extend({"key":k,"match":{"value":v}} for k,v in (metadata_filter or {}).items())
        points=self._call("POST","/points/query",{"query":list(vector),"limit":limit,"with_payload":True,"filter":{"must":must}}).get("result",{}).get("points",[])
        return tuple((_ID_TYPES[x["payload"]["memory_type"]].parse(x["payload"]["memory_id"]),float(x["score"])) for x in points if x.get("payload",{}).get("memory_type") in _ID_TYPES)
    def stats(self):
        result=self._call("GET").get("result",{})
        return VectorIndexStats("qdrant-hnsw",result.get("vectors_count") or result.get("points_count"),self.dimensions,None,True,True)
    def health(self):
        try: self._call("GET"); return BackendHealth.HEALTHY
        except VectorIndexUnavailable: return BackendHealth.UNAVAILABLE
