"""Governed cross-agent learning without agent-to-agent memory transfer.

Raw experiences remain in the learning fabric.  Only a policy-authorized,
deterministically checked abstraction is materialized as ordinary memory.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from syune.core import Confidence, ProcedureId, ProvenanceId, utc_now
from syune.memory import (DefaultAccessPolicy, LifecycleService, MemoryClass, Procedure,
                          Provenance, SecurityEnvelope, Sensitivity, TruthMetadata, TruthState,
                          authorize)
from .verified import AttributionQuality, Experience, OutcomeStatus


class KnowledgeScope(str, Enum):
    AGENT_PRIVATE = "AGENT_PRIVATE"
    PROJECT = "PROJECT"
    DEPARTMENT = "DEPARTMENT"
    ORGANIZATION = "ORGANIZATION"


class OrganizationalKnowledgeState(str, Enum):
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    PROMOTED = "PROMOTED"
    DISPUTED = "DISPUTED"
    DEMOTED = "DEMOTED"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class ScopeRef:
    kind: KnowledgeScope
    organization_id: str
    agent_id: str | None = None
    project_id: str | None = None
    department_id: str | None = None

    def __post_init__(self):
        required = {KnowledgeScope.AGENT_PRIVATE: self.agent_id,
                    KnowledgeScope.PROJECT: self.project_id,
                    KnowledgeScope.DEPARTMENT: self.department_id,
                    KnowledgeScope.ORGANIZATION: self.organization_id}[self.kind]
        if not self.organization_id.strip() or not required or not required.strip():
            raise ValueError("scope requires its organization and concrete identifier")


@dataclass(frozen=True, slots=True)
class ScopeExpansionGrant:
    source: KnowledgeScope
    target: ScopeRef
    policy_id: str
    actor: str
    reason: str
    allowed_task_classes: tuple[str, ...]
    allowed_purposes: tuple[str, ...]
    issued_at: datetime

    def __post_init__(self):
        if not all((self.policy_id.strip(), self.actor.strip(), self.reason.strip())):
            raise ValueError("scope expansion needs policy, actor, and reason")
        if not self.allowed_task_classes or not self.allowed_purposes:
            raise ValueError("scope expansion must constrain task class and purpose")


@dataclass(frozen=True, slots=True)
class SharedExperience:
    experience: Experience
    source_scope: ScopeRef
    generalized_strategy: tuple[str, ...]
    eligible: bool = False
    lineage_keys: tuple[str, ...] = ()
    sensitive_terms: tuple[str, ...] = ()
    task_instance_id: str | None = None
    external_event_id: str | None = None
    replay_id: str | None = None

    def __post_init__(self):
        if self.source_scope.kind is not KnowledgeScope.AGENT_PRIVATE:
            raise ValueError("experience enters the fabric at AGENT_PRIVATE scope")
        if self.experience.security and self.experience.security.organization_scope not in (None, self.source_scope.organization_id):
            raise ValueError("experience organization and security envelope disagree")


@dataclass(frozen=True, slots=True)
class OrganizationalPolicy:
    version: str = "25.1"
    minimum_independent_support: int = 2
    minimum_weighted_support: float = 1.4
    maximum_negative_fraction: float = .25
    demote_weighted_negative: float = 1.2
    revoke_weighted_negative: float = 2.0
    max_evidence: int = 4096


@dataclass(frozen=True, slots=True)
class OrganizationalKnowledge:
    key: str
    revision: int
    state: OrganizationalKnowledgeState
    task_class: str
    conditions: tuple[tuple[str, str], ...]
    environment: str | None
    strategy: tuple[str, ...]
    applicability: tuple[str, ...]
    target_scope: ScopeRef
    purposes: tuple[str, ...]
    confidence: float
    support_ids: tuple[str, ...]
    contradiction_ids: tuple[str, ...]
    independence_clusters: int
    excluded_private_fields: tuple[str, ...]
    promoted_at: datetime | None
    last_supported_at: datetime | None
    procedure_id: ProcedureId | None


def _scope_rank(scope: KnowledgeScope) -> int:
    return {KnowledgeScope.AGENT_PRIVATE: 0, KnowledgeScope.PROJECT: 1,
            KnowledgeScope.DEPARTMENT: 1, KnowledgeScope.ORGANIZATION: 2}[scope]


def _knowledge_key(sample: SharedExperience, target: ScopeRef) -> str:
    material = [sample.experience.task_class, sample.experience.conditions,
                sample.experience.environment, sample.generalized_strategy,
                sample.experience.purpose_constraints, asdict(target)]
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode()).hexdigest()


class SQLiteOrganizationalLearningStore:
    """Private evidence pool plus public-derived knowledge metadata.

    The API intentionally has no unscoped list-all/raw dump operation.
    """
    def __init__(self, path: Path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.lock = threading.RLock()
        self.db.executescript("""PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS cross_agent_experiences(
          id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, organization_id TEXT NOT NULL,
          task_class TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS cross_agent_lookup ON cross_agent_experiences(organization_id,task_class);
        CREATE TABLE IF NOT EXISTS organizational_knowledge(
          key TEXT PRIMARY KEY, revision INTEGER NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS scope_expansion_audit(
          seq INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_key TEXT NOT NULL, occurred_at TEXT NOT NULL,
          source_scope TEXT NOT NULL, target_scope TEXT NOT NULL, policy_id TEXT NOT NULL,
          actor TEXT NOT NULL, reason TEXT NOT NULL, evidence_ids TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS organizational_learning_events(
          seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, ref_id TEXT NOT NULL,
          occurred_at TEXT NOT NULL, payload TEXT NOT NULL);
        """)
        self.db.commit()

    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    @staticmethod
    def _shared_payload(item: SharedExperience) -> str:
        x = item.experience
        return json.dumps({
            "experience_id": str(x.id), "idempotency_key": x.idempotency_key,
            "task_class": x.task_class, "conditions": x.conditions, "strategy": x.strategy,
            "outcome": x.outcome.value, "attribution": x.attribution.value,
            "quality": asdict(x.quality), "occurred_at": x.occurred_at.isoformat(),
            "provenance_id": str(x.provenance.id), "source_id": str(x.provenance.source_id),
            "evaluator_id": x.evaluator_id, "generator_id": x.generator_id,
            "purpose_constraints": x.purpose_constraints, "environment": x.environment,
            "valid_until": x.valid_until.isoformat() if x.valid_until else None,
            "source_scope": {**asdict(item.source_scope), "kind": item.source_scope.kind.value},
            "generalized_strategy": item.generalized_strategy, "eligible": item.eligible,
            "lineage_keys": item.lineage_keys, "sensitive_terms": item.sensitive_terms,
            "task_instance_id": item.task_instance_id, "external_event_id": item.external_event_id,
            "replay_id": item.replay_id, "limitations": x.limitations,
        }, sort_keys=True, separators=(",", ":"))

    def append(self, item: SharedExperience) -> bool:
        raw = self._shared_payload(item); x = item.experience
        with self.lock, self.db:
            row = self.db.execute("SELECT id FROM cross_agent_experiences WHERE idempotency_key=?", (x.idempotency_key,)).fetchone()
            if row: return row[0] == str(x.id)
            self.db.execute("INSERT INTO cross_agent_experiences VALUES(?,?,?,?,?)",
                            (str(x.id), x.idempotency_key, item.source_scope.organization_id, x.task_class, raw))
            self._event("experience_admitted", str(x.id), {"scope": item.source_scope.kind.value})
        return True

    def candidates(self, organization_id: str, task_class: str) -> tuple[dict, ...]:
        rows = self.db.execute("SELECT payload FROM cross_agent_experiences WHERE organization_id=? AND task_class=? ORDER BY id",
                               (organization_id, task_class)).fetchall()
        return tuple(json.loads(row[0]) for row in rows)

    def _event(self, kind: str, ref: str, payload: dict) -> None:
        self.db.execute("INSERT INTO organizational_learning_events(kind,ref_id,occurred_at,payload) VALUES(?,?,?,?)",
                        (kind, ref, utc_now().isoformat(), json.dumps(payload, sort_keys=True)))

    def events(self):
        return tuple(self.db.execute("SELECT kind,ref_id,occurred_at,payload FROM organizational_learning_events ORDER BY seq"))

    def knowledge(self, key: str) -> dict | None:
        row = self.db.execute("SELECT payload FROM organizational_knowledge WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, value: OrganizationalKnowledge, grant: ScopeExpansionGrant) -> None:
        raw = json.dumps({**asdict(value), "state": value.state.value,
                          "target_scope": {**asdict(value.target_scope), "kind": value.target_scope.kind.value},
                          "procedure_id": str(value.procedure_id) if value.procedure_id else None,
                          "promoted_at": value.promoted_at.isoformat() if value.promoted_at else None,
                          "last_supported_at": value.last_supported_at.isoformat() if value.last_supported_at else None},
                         sort_keys=True, default=str)
        self.db.execute("INSERT INTO organizational_knowledge VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET revision=excluded.revision,state=excluded.state,payload=excluded.payload",
                        (value.key, value.revision, value.state.value, raw))
        self.db.execute("INSERT INTO scope_expansion_audit(knowledge_key,occurred_at,source_scope,target_scope,policy_id,actor,reason,evidence_ids) VALUES(?,?,?,?,?,?,?,?)",
                        (value.key, utc_now().isoformat(), grant.source.value, value.target_scope.kind.value,
                         grant.policy_id, grant.actor, grant.reason, json.dumps(value.support_ids)))
        self._event("organizational_" + value.state.value.lower(), value.key,
                    {"revision": value.revision, "independence_clusters": value.independence_clusters,
                     "confidence": value.confidence})

    def scope_audit(self, key: str):
        return tuple(self.db.execute("SELECT source_scope,target_scope,policy_id,actor,reason,evidence_ids FROM scope_expansion_audit WHERE knowledge_key=? ORDER BY seq", (key,)))


class OrganizationalLearningService:
    def __init__(self, memory, store: SQLiteOrganizationalLearningStore, policy: OrganizationalPolicy | None = None, index=None):
        self.memory, self.store, self.policy, self.index = memory, store, policy or OrganizationalPolicy(), index

    def submit(self, item: SharedExperience) -> bool:
        return self.store.append(item)

    @staticmethod
    def _from_raw(raw: dict) -> OrganizationalKnowledge:
        scope = raw["target_scope"]
        return OrganizationalKnowledge(raw["key"], raw["revision"], OrganizationalKnowledgeState(raw["state"]),
            raw["task_class"], tuple(map(tuple, raw["conditions"])), raw["environment"], tuple(raw["strategy"]),
            tuple(raw["applicability"]), ScopeRef(KnowledgeScope(scope["kind"]), scope["organization_id"],
                scope.get("agent_id"), scope.get("project_id"), scope.get("department_id")), tuple(raw["purposes"]),
            raw["confidence"], tuple(raw["support_ids"]), tuple(raw["contradiction_ids"]),
            raw["independence_clusters"], tuple(raw["excluded_private_fields"]),
            datetime.fromisoformat(raw["promoted_at"]) if raw["promoted_at"] else None,
            datetime.fromisoformat(raw["last_supported_at"]) if raw["last_supported_at"] else None,
            ProcedureId.parse(raw["procedure_id"]) if raw["procedure_id"] else None)

    @staticmethod
    def _compatible(raw: dict, sample: SharedExperience, grant: ScopeExpansionGrant) -> bool:
        x = sample.experience
        return (raw["eligible"] and raw["conditions"] == [list(v) for v in x.conditions]
                and raw["environment"] == x.environment
                and tuple(raw["generalized_strategy"]) == sample.generalized_strategy
                and set(raw["purpose_constraints"]) == set(x.purpose_constraints)
                and raw["task_class"] in grant.allowed_task_classes
                and bool(set(raw["purpose_constraints"]) & set(grant.allowed_purposes)))

    @staticmethod
    def _clusters(rows: list[dict]) -> list[list[dict]]:
        groups: list[list[dict]] = []
        for row in rows:
            keys = set(row["lineage_keys"])
            keys.update(filter(None, ("source:" + row["source_id"],
                                      "event:" + row["external_event_id"] if row["external_event_id"] else None,
                                      "replay:" + row["replay_id"] if row["replay_id"] else None,
                                      "task:" + row["task_instance_id"] if row["task_instance_id"] else None)))
            if row["evaluator_id"] == row["generator_id"] and row["evaluator_id"]:
                keys.add("self-evaluator:" + row["evaluator_id"])
            touching = [group for group in groups if keys & group[0]["_cluster_keys"]]
            decorated = {**row, "_cluster_keys": keys}
            if not touching: groups.append([decorated]); continue
            base = touching[0]; base.append(decorated); base[0]["_cluster_keys"].update(keys)
            for extra in touching[1:]:
                base.extend(extra); base[0]["_cluster_keys"].update(extra[0]["_cluster_keys"]); groups.remove(extra)
        return groups

    @staticmethod
    def _secure_abstraction(sample: SharedExperience) -> tuple[bool, tuple[str, ...]]:
        text = " ".join(sample.generalized_strategy).casefold()
        leaked = tuple(term for term in sample.sensitive_terms if term.casefold() in text)
        sensitive = bool(sample.experience.security and sample.experience.security.sensitivity in {Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED})
        safe = bool(sample.generalized_strategy) and not leaked and (not sensitive or bool(sample.sensitive_terms))
        return safe, tuple(sorted(set(sample.sensitive_terms)))

    @staticmethod
    def _envelope(scope: ScopeRef, purposes: tuple[str, ...]) -> SecurityEnvelope:
        values = {"organization_scope": scope.organization_id, "purpose_constraints": purposes,
                  "sensitivity": Sensitivity.INTERNAL, "default_policy": DefaultAccessPolicy.SECURE_DENY}
        if scope.kind is KnowledgeScope.AGENT_PRIVATE: values["agent_scope"] = scope.agent_id
        elif scope.kind is KnowledgeScope.PROJECT: values["project_scope"] = scope.project_id
        elif scope.kind is KnowledgeScope.DEPARTMENT: values["department_scope"] = scope.department_id
        return SecurityEnvelope(**values)

    def promote(self, sample: SharedExperience, target: ScopeRef, grant: ScopeExpansionGrant,
                *, authoritative_policy_conflict: bool = False) -> OrganizationalKnowledge | None:
        if grant.target != target or grant.source is not sample.source_scope.kind or _scope_rank(target.kind) <= _scope_rank(grant.source):
            raise PermissionError("exact explicit upward scope-expansion grant required")
        x = sample.experience
        if target.organization_id != sample.source_scope.organization_id or x.task_class not in grant.allowed_task_classes:
            raise PermissionError("cross-organization or task-class expansion denied")
        if not set(x.purpose_constraints) & set(grant.allowed_purposes):
            raise PermissionError("purpose expansion denied")
        safe, excluded = self._secure_abstraction(sample)
        if not safe or authoritative_policy_conflict:
            self.store._event("promotion_blocked", str(x.id), {"private_abstraction_safe": safe, "policy_conflict": authoritative_policy_conflict})
            self.store.db.commit(); return None
        key = _knowledge_key(sample, target)
        with self.store.lock:
            self.store.db.execute("BEGIN IMMEDIATE")
            try:
                rows = [r for r in self.store.candidates(target.organization_id, x.task_class) if self._compatible(r, sample, grant)]
                rows = rows[:self.policy.max_evidence]
                clusters = self._clusters(rows)
                positive, negative, support_ids, contradiction_ids = 0.0, 0.0, [], []
                positive_clusters = 0
                for cluster in clusters:
                    pos = [r for r in cluster if r["outcome"] == OutcomeStatus.SUCCESS.value and r["attribution"] in (AttributionQuality.DIRECT.value, AttributionQuality.SUPPORTED.value)]
                    neg = [r for r in cluster if r["outcome"] == OutcomeStatus.FAILURE.value]
                    if pos:
                        best = max(pos, key=lambda r: sum(r["quality"].values()) / 5); positive += sum(best["quality"].values()) / 5
                        positive_clusters += 1; support_ids.extend(r["experience_id"] for r in pos)
                    if neg:
                        best = max(neg, key=lambda r: sum(r["quality"].values()) / 5); negative += sum(best["quality"].values()) / 5
                        contradiction_ids.extend(r["experience_id"] for r in neg)
                prior = self.store.knowledge(key); revision = (prior["revision"] + 1) if prior else 1
                fraction = negative / max(.0001, positive + negative)
                if prior and negative >= self.policy.revoke_weighted_negative: state = OrganizationalKnowledgeState.REVOKED
                elif prior and negative >= self.policy.demote_weighted_negative: state = OrganizationalKnowledgeState.DEMOTED
                elif negative and fraction > self.policy.maximum_negative_fraction: state = OrganizationalKnowledgeState.DISPUTED
                elif positive_clusters >= self.policy.minimum_independent_support and positive >= self.policy.minimum_weighted_support: state = OrganizationalKnowledgeState.VERIFIED
                else: state = OrganizationalKnowledgeState.CANDIDATE
                current_support = tuple(sorted(set(support_ids))); current_negative = tuple(sorted(set(contradiction_ids)))
                if prior and tuple(prior["support_ids"]) == current_support and tuple(prior["contradiction_ids"]) == current_negative:
                    self.store.db.commit()
                    return self._from_raw(prior)
                now = utc_now(); pid = ProcedureId(uuid5(NAMESPACE_URL, "organizational:" + key + ":" + str(revision))) if state is OrganizationalKnowledgeState.VERIFIED else None
                value = OrganizationalKnowledge(key, revision, state, x.task_class, x.conditions, x.environment,
                    sample.generalized_strategy, x.limitations, target, tuple(sorted(set(x.purpose_constraints))),
                    max(0.0, min(1.0, (positive-negative)/max(1.0, positive+negative))), current_support,
                    current_negative, positive_clusters, excluded,
                    now if state is OrganizationalKnowledgeState.VERIFIED else None,
                    max((datetime.fromisoformat(r["occurred_at"]) for r in rows if r["outcome"] == OutcomeStatus.SUCCESS.value), default=None), pid)
                if state is OrganizationalKnowledgeState.VERIFIED:
                    provenance = Provenance(ProvenanceId(uuid5(NAMESPACE_URL, "organizational-provenance:" + key + ":" + str(revision))),
                        x.provenance.source_id, now, process_id="syune-organizational-learning", pipeline_version=self.policy.version,
                        parent_provenance_ids=tuple(x.provenance.id for _ in (0,)))
                    truth = TruthMetadata(TruthState.VERIFIED, now, x.valid_from, x.valid_until,
                        revision_of=ProcedureId.parse(prior["procedure_id"]) if prior and prior.get("procedure_id") else None,
                        fact_key="organizational-procedure:" + x.task_class, fact_value=" | ".join(sample.generalized_strategy),
                        context_key=json.dumps([x.conditions, x.environment, x.purpose_constraints], sort_keys=True))
                    procedure = Procedure(pid, sample.generalized_strategy, provenance, Confidence(value.confidence), now,
                                          truth=truth, security=self._envelope(target, value.purposes))
                    if not self.memory.exists(pid): LifecycleService(self.memory).register(procedure, MemoryClass.PROCEDURAL, protected=True, historical_importance=value.confidence)
                    value = replace(value, state=OrganizationalKnowledgeState.PROMOTED)
                elif prior and prior.get("procedure_id") and state in {OrganizationalKnowledgeState.DEMOTED, OrganizationalKnowledgeState.REVOKED}:
                    old_id = ProcedureId.parse(prior["procedure_id"])
                    if self.memory.exists(old_id): LifecycleService(self.memory).archive(old_id, "organizational knowledge " + state.value.lower())
                self.store.save(value, grant); self.store.db.commit()
            except Exception:
                self.store.db.rollback(); raise
        if self.index: self.index.sync()
        return value

    def inspect_raw(self, experience_id: str, access_context):
        row = self.store.db.execute("SELECT payload FROM cross_agent_experiences WHERE id=?", (experience_id,)).fetchone()
        if not row: return None
        raw = json.loads(row[0]); scope = raw["source_scope"]
        envelope = SecurityEnvelope(organization_scope=scope["organization_id"], project_scope=scope.get("project_id"),
            department_scope=scope.get("department_id"), agent_scope=scope.get("agent_id"),
            purpose_constraints=tuple(raw["purpose_constraints"]), sensitivity=Sensitivity.CONFIDENTIAL)
        if not authorize(envelope, access_context).allowed: raise PermissionError("raw evidence access denied")
        return raw

    @staticmethod
    def precedence(local_quality: float, organizational_quality: float, *, local_is_more_specific: bool,
                   local_valid: bool, organizational_valid: bool, authoritative_policy_conflict: bool = False) -> str:
        if authoritative_policy_conflict: return "AUTHORITATIVE_POLICY"
        if local_valid and not organizational_valid: return "LOCAL"
        if organizational_valid and not local_valid: return "ORGANIZATIONAL"
        if local_valid and local_is_more_specific and local_quality >= organizational_quality: return "LOCAL"
        return "ORGANIZATIONAL" if organizational_valid else "ABSTAIN"
