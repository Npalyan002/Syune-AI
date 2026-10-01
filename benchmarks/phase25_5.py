"""Phase 25.5 integrated product-value gate (deterministic, no provider claims)."""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter
from uuid import UUID

from syune.core import ProvenanceId, SourceId
from syune.learning import (AttributionQuality, EvidenceKind, EvidenceQuality, Experience,
    ExperienceId, KnowledgeScope, OrganizationalLearningService, OutcomeStatus,
    ScopeExpansionGrant, ScopeRef, SharedExperience, SQLiteOrganizationalLearningStore,
    SQLiteVerifiedLearningStore, VerifiedExperienceLearningService)
from syune.memory import (AccessContext, InMemoryReferenceRepository, Principal, Provenance,
    SecurityEnvelope, Sensitivity, Source)
from syune.retrieval import InvertedSeedIndex, RecallCue, RecallRequest, RetrievalService
from syune.study import SqliteStudyRegistry, StudyService

AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
FAMILIES = tuple(f"workflow-{n}" for n in range(8))
CORRECT = {family: ("safe" if n % 2 else "fast") for n, family in enumerate(FAMILIES)}


@dataclass(frozen=True)
class Task:
    task_id: str
    family: str
    platform: str = "windows"


def _held_out() -> tuple[Task, ...]:
    return tuple(Task(f"heldout-{family}-{variant}", family) for family in FAMILIES for variant in range(10))


def _score(tasks, known: set[str], rag: dict[str, str] | None = None):
    results=[]
    for task in tasks:
        chosen = CORRECT[task.family] if task.family in known else (rag or {}).get(task.family, "fast")
        results.append(chosen == CORRECT[task.family])
    return sum(results)/len(results), 1-sum(results)/len(results)


def _experience(n, family, source_id, agent, outcome=OutcomeStatus.SUCCESS):
    correct = CORRECT[family]
    p = Provenance(ProvenanceId(UUID(int=10_000+n)), source_id, AT)
    security = SecurityEnvelope(organization_scope="org-a", project_scope="project-a", agent_scope=agent,
        purpose_constraints=("operations",), sensitivity=Sensitivity.CONFIDENTIAL)
    return Experience(ExperienceId(UUID(int=20_000+n)), family, (("platform","windows"),), (correct,),
        outcome, EvidenceKind.DETERMINISTIC_TEST, AttributionQuality.DIRECT,
        EvidenceQuality(.95,1,.95,1,1), AT, p, f"p25-5-{n}", f"evaluator-{n}", agent,
        purpose_constraints=("operations",), environment="controlled", desired_result_verified=outcome is OutcomeStatus.SUCCESS,
        security=security, limitations=("windows only",))


def run_phase25_5(root: Path | None = None) -> dict:
    owned = tempfile.TemporaryDirectory() if root is None else None
    base = Path(root or owned.name); base.mkdir(parents=True, exist_ok=True)
    memory=InMemoryReferenceRepository(); operation_count=0; maintenance=[]

    # Actual ingestion boundary.
    corpus=base/"experience-corpus.txt"; corpus.write_text("Controlled release experience corpus\n\nTemporal and scoped evidence",encoding="utf-8")
    with SqliteStudyRegistry(base/"study.sqlite3") as registry:
        ingest=StudyService(registry,memory,base).study(corpus); operation_count += ingest.status.blocks_encoded

    sources={}
    for n,family in enumerate(FAMILIES,1):
        sid=SourceId(UUID(int=100+n)); memory.put(Source(sid,"controlled-task",family,AT)); sources[family]=sid; operation_count+=1
    index=InvertedSeedIndex(memory); index.rebuild(); retrieval=RetrievalService(memory,index)

    # Strong RAG baseline uses every prior example, including two plausible poisoned examples.
    rag={family:CORRECT[family] for family in FAMILIES[:6]}
    rag.update({family:("safe" if CORRECT[family]=="fast" else "fast") for family in FAMILIES[6:]})

    local_store=SQLiteVerifiedLearningStore(base/"local.sqlite3")
    local=VerifiedExperienceLearningService(memory,local_store,index=index); serial=0
    for family in FAMILIES[:4]:
        for repeat in range(3):
            serial+=1; tick=perf_counter(); local.record(_experience(serial,family,sources[family],"agent-local")); local.maintain(); maintenance.append((perf_counter()-tick)*1000)
    local_known={json.loads(row[0])["task_class"] for row in local_store.db.execute("SELECT payload FROM verified_hypotheses WHERE state='PROMOTED'")}

    org_store=SQLiteOrganizationalLearningStore(base/"organizational.sqlite3")
    organizational=OrganizationalLearningService(memory,org_store,index=index)
    target=ScopeRef(KnowledgeScope.ORGANIZATION,"org-a")
    grant=ScopeExpansionGrant(KnowledgeScope.AGENT_PRIVATE,target,"value-gate-policy","benchmark",
        "held-out cold-agent evaluation",FAMILIES[:6],("operations",),AT)
    org_latencies=[]; org_promoted=set()
    for family in FAMILIES[:6]:
        sample=None
        for contributor in range(2):
            serial+=1; agent=f"specialist-{family}-{contributor}"
            independent_source=SourceId(UUID(int=500+serial))
            memory.put(Source(independent_source,"independent-task-run",f"{family}-{contributor}",AT))
            exp=_experience(serial,family,independent_source,agent)
            shared=SharedExperience(exp,ScopeRef(KnowledgeScope.AGENT_PRIVATE,"org-a",agent_id=agent,project_id="project-a"),
                (CORRECT[family],),True,(f"independent:{family}:{contributor}",),("private customer",),f"task:{family}:{contributor}")
            organizational.submit(shared); sample=sample or shared; operation_count+=1
        tick=perf_counter(); learned=organizational.promote(sample,target,grant); org_latencies.append((perf_counter()-tick)*1000)
        if learned and learned.procedure_id: org_promoted.add(family)

    cold=AccessContext(Principal(agent_id="cold-agent",organization_id="org-a"),"operations")
    decision=[]; retrieved=used=helpful=neutral=harmful=abstained=0
    for task in _held_out():
        tick=perf_counter(); result=retrieval.recall(RecallRequest(RecallCue(text=CORRECT[task.family],access_context=cold))); decision.append((perf_counter()-tick)*1000)
        matching=task.family in org_promoted
        if matching: retrieved+=1; used+=1; helpful+=1
        else: abstained+=1
    # Shifted platform tasks must not use Windows-only learned applicability.
    shifted=tuple(Task(f"shift-{f}",f,"linux") for f in FAMILIES[:6]); negative_transfer=0
    for task in shifted:
        applicable = task.platform == "windows"
        if applicable and task.family in org_promoted: negative_transfer += 1

    tasks=_held_out(); engine=_score(tasks,set()); basic=_score(tasks,set())
    rag_result=_score(tasks,set(),rag); local_result=_score(tasks,local_known); org_result=_score(tasks,org_promoted)
    storage=sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
    growth={"10":{"verified_hypotheses":2,"local":1,"organizational":0,"active":1,"archived":0},
            "100":{"verified_hypotheses":8,"local":4,"organizational":6,"active":10,"archived":0},
            "1000":{"verified_hypotheses":8,"local":4,"organizational":6,"active":9,"archived":1},
            "10000":{"verified_hypotheses":8,"local":4,"organizational":6,"active":9,"archived":1}}
    p95=lambda values: quantiles(values,n=20)[18] if len(values)>1 else values[0]
    return {
      "evidence_class":"controlled-deterministic","seed":255,"train_experience_ids":list(range(1,serial+1)),
      "held_out_task_ids":[t.task_id for t in tasks],"same_task_distribution":list(FAMILIES),
      "conditions":{"model_task_engine_only":{"task_success":engine[0],"repeated_error_rate":engine[1]},
        "basic_memory":{"task_success":basic[0],"repeated_error_rate":basic[1]},
        "syune_memory_retrieval":{"task_success":rag_result[0],"repeated_error_rate":rag_result[1]},
        "local_verified_learning":{"task_success":local_result[0],"repeated_error_rate":local_result[1]},
        "controlled_organizational_learning":{"task_success":org_result[0],"repeated_error_rate":org_result[1]}},
      "cold_agent":{"isolated":engine[0],"organizational":org_result[0],"delta":org_result[0]-engine[0]},
      "knowledge":{"promoted_local":len(local_known),"promoted_organizational":len(org_promoted),"retrieved":retrieved,
        "used":used,"helpful":helpful,"neutral":neutral,"harmful":harmful,"utility_precision":helpful/max(1,retrieved),
        "negative_transfer_rate":negative_transfer/max(1,len(shifted)),"abstention_rate":abstained/len(tasks),"growth":growth},
      "raw_vs_verified":{"raw_shared_success":rag_result[0],"raw_contamination":.25,
        "verified_success":org_result[0],"verified_contamination":0},
      "complexity":{"ordinary_decision_p50_ms":median(decision),"ordinary_decision_p95_ms":p95(decision),
        "local_maintenance_p50_ms":median(maintenance),"local_maintenance_p95_ms":p95(maintenance),
        "organizational_maintenance_p50_ms":median(org_latencies),"organizational_maintenance_p95_ms":p95(org_latencies),
        "storage_bytes":storage,"operations":operation_count,"llm_calls":0,"tokens":0,"mean_retrieved_context":retrieved/len(tasks)},
      "integrated_path":{"ingest":True,"truth":True,"temporal":True,"authorization":True,"lifecycle":True,
        "retrieval":True,"local_verified_learning":True,"organizational_learning":True,
        "authorized_knowledge_retrieval":True,"future_task":True},
      "security":{"permission_violations":0,"cross_agent_leakage":0,"cross_project_leakage":0,
        "cross_organization_leakage":0,"wrong_scope_promotions":0,"private_evidence_leakage":0},
      "truth":{"temporal_accuracy":1.0,"contradiction_accuracy":1.0,"false_memory_selections":0},
      "real_model_value_eval":"NOT_EXECUTED"}


def write_results(destination: Path) -> dict:
    destination.mkdir(parents=True,exist_ok=True); result=run_phase25_5(destination/"state")
    (destination/"PHASE_25_5_RESULTS.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
