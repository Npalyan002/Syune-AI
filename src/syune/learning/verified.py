"""Verified experience learning: evidence-backed, reversible procedure promotion."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from syune.core import Confidence, OpaqueId, ProcedureId, ProvenanceId, utc_now
from syune.memory import (LifecycleService, MemoryClass, Procedure, Provenance, SecurityEnvelope,
                          TruthMetadata, TruthState)


class ExperienceId(OpaqueId): __slots__=()
class HypothesisId(OpaqueId): __slots__=()


class OutcomeStatus(str,Enum):
    SUCCESS="SUCCESS"; FAILURE="FAILURE"; PARTIAL="PARTIAL"; UNKNOWN="UNKNOWN"


class EvidenceKind(str,Enum):
    TASK_RESULT="TASK_RESULT"; EXTERNAL_EVALUATION="EXTERNAL_EVALUATION"; HUMAN_FEEDBACK="HUMAN_FEEDBACK"
    DETERMINISTIC_TEST="DETERMINISTIC_TEST"; MEASURED_METRIC="MEASURED_METRIC"; SYSTEM_OBSERVATION="SYSTEM_OBSERVATION"


class AttributionQuality(str,Enum):
    DIRECT="DIRECT"; SUPPORTED="SUPPORTED"; POSSIBLE="POSSIBLE"; UNKNOWN="UNKNOWN"; CONFOUNDED="CONFOUNDED"


class FeedbackKind(str,Enum):
    AUTHORITATIVE_INSTRUCTION="AUTHORITATIVE_INSTRUCTION"; PREFERENCE="PREFERENCE"
    EVALUATION="EVALUATION"; CASUAL="CASUAL"


class VerifiedLearningState(str,Enum):
    OBSERVED="OBSERVED"; CANDIDATE="CANDIDATE"; SUPPORTED="SUPPORTED"; VERIFIED="VERIFIED"
    PROMOTED="PROMOTED"; DISPUTED="DISPUTED"; DEMOTED="DEMOTED"; REVOKED="REVOKED"


@dataclass(frozen=True,slots=True)
class EvidenceQuality:
    source_reliability: float
    directness: float
    independence: float
    verification: float
    scope_match: float
    def __post_init__(self):
        if any(not 0<=x<=1 for x in asdict(self).values()): raise ValueError("evidence quality values must be within [0,1]")
    @property
    def score(self): return sum(asdict(self).values())/5


@dataclass(frozen=True,slots=True)
class Experience:
    id: ExperienceId
    task_class: str
    conditions: tuple[tuple[str,str],...]
    strategy: tuple[str,...]
    outcome: OutcomeStatus
    evidence_kind: EvidenceKind
    attribution: AttributionQuality
    quality: EvidenceQuality
    occurred_at: datetime
    provenance: Provenance
    idempotency_key: str
    evaluator_id: str | None = None
    generator_id: str | None = None
    feedback_kind: FeedbackKind | None = None
    principal_scope: str | None = None
    purpose_constraints: tuple[str,...] = ()
    environment: str | None = None
    desired_result_verified: bool = False
    independence_key: str | None = None
    security: SecurityEnvelope | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    limitations: tuple[str,...] = ()
    def __post_init__(self):
        if type(self.id) is not ExperienceId or not self.task_class.strip() or not self.strategy: raise ValueError("typed experience, task class, and strategy required")
        if not self.idempotency_key.strip(): raise ValueError("idempotency key required")
        if self.outcome is OutcomeStatus.SUCCESS and not self.desired_result_verified:
            raise ValueError("SUCCESS requires verified desired result; completion alone is insufficient")


@dataclass(frozen=True,slots=True)
class LearningHypothesis:
    id: HypothesisId
    key: str
    state: VerifiedLearningState
    task_class: str
    conditions: tuple[tuple[str,str],...]
    strategy: tuple[str,...]
    supporting_experience_ids: tuple[ExperienceId,...]
    contradicting_experience_ids: tuple[ExperienceId,...]
    independent_support: int
    independent_negative: int
    confidence: float
    learned_at: datetime
    last_supported_at: datetime | None
    security: SecurityEnvelope | None
    purpose_constraints: tuple[str,...]
    limitations: tuple[str,...]
    procedure_id: ProcedureId | None = None


@dataclass(frozen=True,slots=True)
class VerificationPolicy:
    version: str="1"
    minimum_support: int=3
    minimum_independent_support: int=2
    minimum_quality: float=.65
    acceptable_attribution: tuple[AttributionQuality,...]=(AttributionQuality.DIRECT,AttributionQuality.SUPPORTED)
    maximum_negative_ratio: float=.25
    demote_independent_failures: int=2
    revoke_independent_failures: int=3
    allow_scope_expansion: bool=False
    max_batch: int=256
    maximum_evidence_per_hypothesis: int=2048
    def __post_init__(self):
        if self.minimum_support<2 or self.minimum_independent_support<2 or not 0<=self.maximum_negative_ratio<1 or self.max_batch<1 or self.maximum_evidence_per_hypothesis<self.minimum_support:
            raise ValueError("unsafe verification policy")


def hypothesis_key(experience:Experience)->str:
    material=json.dumps([experience.task_class,experience.conditions,experience.strategy,experience.environment,
                         experience.principal_scope,experience.purpose_constraints,repr(experience.security)],sort_keys=True,separators=(",",":"))
    return hashlib.sha256(material.encode()).hexdigest()


class SQLiteVerifiedLearningStore:
    def __init__(self,path:Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.db=sqlite3.connect(self.path)
        self.db.executescript("""PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS verified_experiences(id TEXT PRIMARY KEY,idempotency_key TEXT UNIQUE,key TEXT NOT NULL,payload TEXT NOT NULL,processed INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS verified_experiences_key ON verified_experiences(key,processed);
        CREATE TABLE IF NOT EXISTS verified_hypotheses(key TEXT PRIMARY KEY,payload TEXT NOT NULL,state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS verified_learning_events(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,ref_id TEXT NOT NULL,occurred_at TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS verified_policy_audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,version TEXT NOT NULL,occurred_at TEXT NOT NULL,payload TEXT NOT NULL);""")
        self.db.commit()
    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self,*_): self.close()
    @staticmethod
    def _security(value):
        if value is None:return None
        raw=asdict(value); raw["sensitivity"]=value.sensitivity.value; raw["default_policy"]=value.default_policy.value; return raw
    @staticmethod
    def _provenance(value):
        return {"id":str(value.id),"source_id":str(value.source_id),"created_at":value.created_at.isoformat(),
                "parents":[str(x) for x in value.parent_provenance_ids]}
    def _encode_experience(self,x):
        return json.dumps({"id":str(x.id),"task_class":x.task_class,"conditions":x.conditions,"strategy":x.strategy,"outcome":x.outcome.value,
          "evidence_kind":x.evidence_kind.value,"attribution":x.attribution.value,"quality":asdict(x.quality),"occurred_at":x.occurred_at.isoformat(),
          "provenance":self._provenance(x.provenance),"idempotency_key":x.idempotency_key,"evaluator_id":x.evaluator_id,"generator_id":x.generator_id,
          "feedback_kind":x.feedback_kind.value if x.feedback_kind else None,"principal_scope":x.principal_scope,"purpose_constraints":x.purpose_constraints,
          "environment":x.environment,"desired_result_verified":x.desired_result_verified,"independence_key":x.independence_key,"security":self._security(x.security),
          "valid_from":x.valid_from.isoformat() if x.valid_from else None,"valid_until":x.valid_until.isoformat() if x.valid_until else None,"limitations":x.limitations},separators=(",",":"),sort_keys=True)
    @staticmethod
    def _decode_security(raw):
        if raw is None:return None
        from syune.memory import DefaultAccessPolicy,Sensitivity
        raw=dict(raw); raw["sensitivity"]=Sensitivity(raw["sensitivity"]); raw["default_policy"]=DefaultAccessPolicy(raw["default_policy"]); return SecurityEnvelope(**raw)
    def _decode_experience(self,raw):
        v=json.loads(raw); p=v["provenance"]
        provenance=Provenance(ProvenanceId.parse(p["id"]),__import__("syune.core",fromlist=["SourceId"]).SourceId.parse(p["source_id"]),datetime.fromisoformat(p["created_at"]),parent_provenance_ids=tuple(ProvenanceId.parse(x) for x in p["parents"]))
        return Experience(ExperienceId.parse(v["id"]),v["task_class"],tuple(map(tuple,v["conditions"])),tuple(v["strategy"]),OutcomeStatus(v["outcome"]),EvidenceKind(v["evidence_kind"]),AttributionQuality(v["attribution"]),EvidenceQuality(**v["quality"]),datetime.fromisoformat(v["occurred_at"]),provenance,v["idempotency_key"],v["evaluator_id"],v["generator_id"],FeedbackKind(v["feedback_kind"]) if v["feedback_kind"] else None,v["principal_scope"],tuple(v["purpose_constraints"]),v["environment"],v["desired_result_verified"],v["independence_key"],self._decode_security(v["security"]),datetime.fromisoformat(v["valid_from"]) if v["valid_from"] else None,datetime.fromisoformat(v["valid_until"]) if v["valid_until"] else None,tuple(v["limitations"]))
    def append(self,x):
        existing=self.db.execute("SELECT id FROM verified_experiences WHERE idempotency_key=?",(x.idempotency_key,)).fetchone()
        if existing:return existing[0]==str(x.id)
        raw=self._encode_experience(x); key=hypothesis_key(x)
        with self.db:
            self.db.execute("INSERT INTO verified_experiences VALUES(?,?,?,?,0)",(str(x.id),x.idempotency_key,key,raw))
            self.event("experience_recorded",str(x.id),{"key":key})
        return True
    def experiences(self,key,limit=None):
        sql="SELECT payload FROM verified_experiences WHERE key=? ORDER BY id DESC"+(" LIMIT ?" if limit else "")
        args=(key,limit) if limit else (key,)
        return tuple(reversed(tuple(self._decode_experience(r[0]) for r in self.db.execute(sql,args))))
    def pending_keys(self,limit): return tuple(r[0] for r in self.db.execute("SELECT DISTINCT key FROM verified_experiences WHERE processed=0 ORDER BY key LIMIT ?",(limit,)))
    def mark_processed(self,key): self.db.execute("UPDATE verified_experiences SET processed=1 WHERE key=?",(key,))
    def save_hypothesis(self,x):
        raw=json.dumps({"id":str(x.id),"key":x.key,"state":x.state.value,"task_class":x.task_class,"conditions":x.conditions,"strategy":x.strategy,
         "support":[str(i) for i in x.supporting_experience_ids],"negative":[str(i) for i in x.contradicting_experience_ids],"independent_support":x.independent_support,
         "independent_negative":x.independent_negative,"confidence":x.confidence,"learned_at":x.learned_at.isoformat(),"last_supported_at":x.last_supported_at.isoformat() if x.last_supported_at else None,
         "security":self._security(x.security),"purpose_constraints":x.purpose_constraints,"limitations":x.limitations,"procedure_id":str(x.procedure_id) if x.procedure_id else None},sort_keys=True,separators=(",",":"))
        self.db.execute("INSERT INTO verified_hypotheses VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,state=excluded.state",(x.key,raw,x.state.value))
    def hypothesis(self,key):
        row=self.db.execute("SELECT payload FROM verified_hypotheses WHERE key=?",(key,)).fetchone()
        if not row:return None
        v=json.loads(row[0]); return LearningHypothesis(HypothesisId.parse(v["id"]),v["key"],VerifiedLearningState(v["state"]),v["task_class"],tuple(map(tuple,v["conditions"])),tuple(v["strategy"]),tuple(ExperienceId.parse(i) for i in v["support"]),tuple(ExperienceId.parse(i) for i in v["negative"]),v["independent_support"],v["independent_negative"],v["confidence"],datetime.fromisoformat(v["learned_at"]),datetime.fromisoformat(v["last_supported_at"]) if v["last_supported_at"] else None,self._decode_security(v["security"]),tuple(v["purpose_constraints"]),tuple(v["limitations"]),ProcedureId.parse(v["procedure_id"]) if v["procedure_id"] else None)
    def event(self,kind,ref,payload): self.db.execute("INSERT INTO verified_learning_events(event_type,ref_id,occurred_at,payload) VALUES(?,?,?,?)",(kind,ref,utc_now().isoformat(),json.dumps(payload,sort_keys=True)))
    def audit_policy(self,policy):
        with self.db:self.db.execute("INSERT INTO verified_policy_audit(version,occurred_at,payload) VALUES(?,?,?)",(policy.version,utc_now().isoformat(),json.dumps({**asdict(policy),"acceptable_attribution":[x.value for x in policy.acceptable_attribution]},sort_keys=True)))
    def events(self): return tuple(self.db.execute("SELECT event_type,ref_id,occurred_at,payload FROM verified_learning_events ORDER BY seq"))


class VerifiedExperienceLearningService:
    def __init__(self,memory,store,policy=None,index=None):
        self.memory=memory; self.store=store; self.policy=policy or VerificationPolicy(); self.index=index; self.latencies_ms=[]; store.audit_policy(self.policy)
    def record(self,experience): return self.store.append(experience)
    @staticmethod
    def _independence(experience):
        # Self-grading is explicitly correlated and cannot create an independent confirmation.
        if experience.evaluator_id and experience.evaluator_id==experience.generator_id:return "self:"+experience.evaluator_id
        return experience.independence_key or f"{experience.provenance.source_id}:{experience.evaluator_id or 'unknown'}"
    def _evaluate(self,key):
        experiences=self.store.experiences(key,self.policy.maximum_evidence_per_hypothesis); first=experiences[0]; acceptable=self.policy.acceptable_attribution
        usable=[x for x in experiences if x.quality.score>=self.policy.minimum_quality and x.attribution in acceptable]
        positives=[x for x in usable if x.outcome is OutcomeStatus.SUCCESS]
        negatives=[x for x in usable if x.outcome is OutcomeStatus.FAILURE]
        positive_ind={self._independence(x) for x in positives}; negative_ind={self._independence(x) for x in negatives}
        # A model's self-evaluation never contributes more than one correlated source.
        independent_support=len(positive_ind); independent_negative=len(negative_ind)
        ratio=len(negatives)/max(1,len(positives)+len(negatives)); prior=self.store.hypothesis(key); now=utc_now()
        if prior and prior.state in {VerifiedLearningState.PROMOTED,VerifiedLearningState.DEMOTED} and independent_negative>=self.policy.revoke_independent_failures: state=VerifiedLearningState.REVOKED
        elif prior and prior.state is VerifiedLearningState.PROMOTED and independent_negative>=self.policy.demote_independent_failures: state=VerifiedLearningState.DEMOTED
        elif negatives and ratio>self.policy.maximum_negative_ratio: state=VerifiedLearningState.DISPUTED
        elif len(positives)>=self.policy.minimum_support and independent_support>=self.policy.minimum_independent_support: state=VerifiedLearningState.VERIFIED
        elif len(positives)>=2: state=VerifiedLearningState.SUPPORTED
        elif len(positives)==1: state=VerifiedLearningState.CANDIDATE
        else: state=VerifiedLearningState.OBSERVED
        confidence=max(0,min(1,(sum(x.quality.score for x in positives)-sum(x.quality.score for x in negatives))/max(1,len(usable))))
        return LearningHypothesis(HypothesisId(uuid5(NAMESPACE_URL,"hypothesis:"+key)),key,state,first.task_class,first.conditions,first.strategy,tuple(x.id for x in positives),tuple(x.id for x in negatives),independent_support,independent_negative,confidence,prior.learned_at if prior else now,max((x.occurred_at for x in positives),default=None),first.security,first.purpose_constraints,tuple(sorted(set(sum((x.limitations for x in experiences),())))),prior.procedure_id if prior else None)
    def _apply(self,hypothesis):
        prior=self.store.hypothesis(hypothesis.key); value=hypothesis
        if hypothesis.state is VerifiedLearningState.VERIFIED:
            first=self.store.experiences(hypothesis.key)[0]
            pid=ProcedureId(uuid5(NAMESPACE_URL,"learned-procedure:"+hypothesis.key))
            provenance=Provenance(ProvenanceId(uuid5(NAMESPACE_URL,"learned-provenance:"+hypothesis.key)),first.provenance.source_id,utc_now(),process_id="verified-experience-learning",pipeline_version=self.policy.version,parent_provenance_ids=tuple(x.provenance.id for x in self.store.experiences(hypothesis.key)))
            truth=TruthMetadata(TruthState.VERIFIED,utc_now(),first.valid_from,first.valid_until,fact_key="learned-procedure:"+hypothesis.task_class,fact_value=" | ".join(hypothesis.strategy),context_key=json.dumps(hypothesis.conditions))
            procedure=Procedure(pid,hypothesis.strategy,provenance,Confidence(hypothesis.confidence),utc_now(),truth=truth,security=hypothesis.security)
            if not self.memory.exists(pid): LifecycleService(self.memory).register(procedure,MemoryClass.PROCEDURAL,protected=True,historical_importance=hypothesis.confidence)
            value=replace(hypothesis,state=VerifiedLearningState.PROMOTED,procedure_id=pid)
        elif hypothesis.state in {VerifiedLearningState.DEMOTED,VerifiedLearningState.REVOKED} and hypothesis.procedure_id and self.memory.exists(hypothesis.procedure_id):
            procedure=self.memory.get(hypothesis.procedure_id)
            if hypothesis.state is VerifiedLearningState.REVOKED:
                self.memory.replace(replace(procedure,truth=replace(procedure.truth,state=TruthState.INVALIDATED,recorded_at=utc_now())),"LEARNING_REVOKED")
            LifecycleService(self.memory).archive(hypothesis.procedure_id,"learned knowledge "+hypothesis.state.value.lower())
        self.store.save_hypothesis(value)
        event={VerifiedLearningState.PROMOTED:"knowledge_promoted",VerifiedLearningState.DEMOTED:"knowledge_demoted",VerifiedLearningState.REVOKED:"knowledge_revoked",VerifiedLearningState.DISPUTED:"hypothesis_disputed",VerifiedLearningState.VERIFIED:"knowledge_verified",VerifiedLearningState.SUPPORTED:"hypothesis_supported",VerifiedLearningState.CANDIDATE:"hypothesis_created",VerifiedLearningState.OBSERVED:"pattern_detected"}[value.state]
        self.store.event(event,str(value.id),{"support":value.independent_support,"negative":value.independent_negative,"confidence":value.confidence})
        if self.index:self.index.sync()
        return value
    def maintain(self,limit=None):
        started=perf_counter(); keys=self.store.pending_keys(min(limit or self.policy.max_batch,self.policy.max_batch)); results=[]
        with self.store.db:
            for key in keys:
                results.append(self._apply(self._evaluate(key))); self.store.mark_processed(key)
        self.latencies_ms.append((perf_counter()-started)*1000); return tuple(results)
    def explain(self,key):
        item=self.store.hypothesis(key)
        if item is None:return None
        return {"state":item.state.value,"supporting_experiences":[str(x) for x in item.supporting_experience_ids],"contradicting_experiences":[str(x) for x in item.contradicting_experience_ids],"independent_support":item.independent_support,"independent_negative":item.independent_negative,"confidence":item.confidence,"scope":item.security,"purpose":item.purpose_constraints,"limitations":item.limitations,"procedure_id":str(item.procedure_id) if item.procedure_id else None,"revocation_threshold":self.policy.revoke_independent_failures}
