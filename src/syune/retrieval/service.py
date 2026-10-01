"""Deterministic bounded associative recall over structural memory."""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from math import exp
from time import perf_counter
from typing import Callable

from syune.core import SourceId, utc_now
from syune.memory import (
    AccessAuditEvent, ActivationState, Association, ContradictionKind, QueryMode, Source,
    TruthState, VerificationPolicy, classify_disagreement, temporally_eligible,
    authorize, LifecycleState,
)
from syune.memory.model import NodeId
from syune.memory.repository import MemoryObject, MemoryRepository
from .index import SeedIndex
from .hybrid import RetrieverKind, analyze_query, reciprocal_rank_fusion
from .model import (
    NullPlasticityView, PlasticityView, RecallCandidate, RecallRequest, RecallResult, RetrievalConfig,
    RetrievalError, RetrievalErrorCode,
)


def _key(entity_id: NodeId) -> tuple[str, str]:
    return type(entity_id).__name__, str(entity_id)


class RetrievalService:
    def __init__(self, memory: MemoryRepository, index: SeedIndex,
                 config: RetrievalConfig | None = None,
                 materialization_check: Callable[[SourceId], str | None] | None = None,
                 plasticity: PlasticityView | None = None):
        self.memory = memory
        self.index = index
        self.config = config or RetrievalConfig()
        self.materialization_check = materialization_check
        self.plasticity = plasticity or NullPlasticityView()
        self.access_events: list[AccessAuditEvent] = []

    def recall(self, request: RecallRequest) -> RecallResult:
        if not isinstance(request, RecallRequest):
            raise RetrievalError(RetrievalErrorCode.INVALID_REQUEST, "RecallRequest required")
        cfg = self.config
        started = perf_counter()
        marks: dict[str, float] = {}
        truncated: set[str] = set()
        seeds: dict[NodeId, float] = {}
        reasons: dict[NodeId, set[str]] = defaultdict(set)
        lexical: dict[NodeId, set[str]] = defaultdict(set)
        cue = request.cue
        analysis = analyze_query(cue.text, bool(cue.entity_ids or cue.source_ids or cue.context_ids))
        found_by: dict[NodeId, set[str]] = defaultdict(set)

        def add_seed(entity_id: NodeId, value: float, reason: str) -> None:
            if entity_id not in seeds and len(seeds) >= cfg.max_candidates:
                truncated.add("candidates")
                return
            if not self.memory.exists(entity_id):
                raise RetrievalError(RetrievalErrorCode.MISSING_ENTITY, f"missing explicit/structural entity: {entity_id}")
            if hasattr(self.memory,"lifecycle"):
                state=self.memory.lifecycle(entity_id).state
                if state is not LifecycleState.ACTIVE and not (cue.include_archived and state is LifecycleState.ARCHIVED): return
            seeds[entity_id] = max(seeds.get(entity_id, 0.0), value)
            reasons[entity_id].add(reason)
            if reason.startswith("lexical:"): found_by[entity_id].add(RetrieverKind.LEXICAL.value)
            elif reason in {"exact_id", "source_id", "context_id"}: found_by[entity_id].add(RetrieverKind.EXACT.value)
            elif reason.startswith("entity:"): found_by[entity_id].add(RetrieverKind.ENTITY.value)
            elif reason.startswith("semantic:"): found_by[entity_id].add(RetrieverKind.SEMANTIC.value)

        try:
            explicit = tuple(dict.fromkeys((*cue.entity_ids, *cue.context_ids)))
            if len(explicit) > cfg.max_explicit_seeds:
                truncated.add("explicit_seeds")
            for entity_id in explicit[:cfg.max_explicit_seeds]:
                add_seed(entity_id, 1.0, "context_id" if entity_id in cue.context_ids else "exact_id")
            if len(cue.source_ids) > cfg.max_explicit_seeds:
                truncated.add("explicit_seeds")
            for source_id in cue.source_ids[:cfg.max_explicit_seeds]:
                add_seed(source_id, 1.0, "source_id")
                for entity_id in self.index.source_ids(source_id, cfg.max_lexical_seeds):
                    add_seed(entity_id, 0.8, "source_provenance")
            if cue.text:
                if RetrieverKind.EXACT in analysis.routes and hasattr(self.index, "exact"):
                    for hit in self.index.exact(cue.text, cfg.max_lexical_seeds):
                        add_seed(hit.entity_id, 1.0, "exact:text")
                        found_by[hit.entity_id].add(RetrieverKind.EXACT.value)
                if RetrieverKind.ENTITY in analysis.routes and hasattr(self.index, "entity"):
                    for hit in self.index.entity(cue.text, cfg.max_lexical_seeds):
                        coverage = len(set(hit.matched_tokens) & set(analysis.tokens)) / max(1, len(analysis.tokens))
                        if coverage < 0.5 and not self.memory.associations_for(hit.entity_id):
                            continue
                        add_seed(hit.entity_id, hit.score, "entity:name")
                if RetrieverKind.LEXICAL in analysis.routes:
                    for hit in self.index.lexical(cue.text, cfg.max_lexical_seeds):
                        # Weak isolated overlap is noise; graph-linked seeds remain useful for multi-hop.
                        coverage = len(hit.matched_tokens) / max(1, len(analysis.tokens))
                        if coverage < 0.5 and not self.memory.associations_for(hit.entity_id):
                            continue
                        add_seed(hit.entity_id, hit.score, f"lexical:{hit.field}")
                        lexical[hit.entity_id].update(hit.matched_tokens)
                if RetrieverKind.SEMANTIC in analysis.routes and hasattr(self.index, "semantic"):
                    for hit in self.index.semantic(cue.text, cfg.max_lexical_seeds):
                        if hit.score >= 0.35: add_seed(hit.entity_id, hit.score, "semantic:vector")
                if not seeds and RetrieverKind.SEMANTIC in analysis.fallback and hasattr(self.index, "semantic"):
                    for hit in self.index.semantic(cue.text, min(8, cfg.max_lexical_seeds)):
                        if hit.score >= 0.70: add_seed(hit.entity_id, hit.score, "semantic:fallback")
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError(RetrievalErrorCode.REPOSITORY_FAILURE, "seed generation failed") from exc
        marks["seed"] = (perf_counter() - started) * 1000
        if not seeds:
            return RecallResult(request.request_id, (), (), (("seeds", 0), ("edges", 0), ("candidates", 0)),
                                (("seed", marks["seed"]), ("expansion", 0.0), ("scoring", 0.0),
                                 ("total", (perf_counter() - started) * 1000)),
                                (), cfg.version, "INSUFFICIENT_EVIDENCE",
                                tuple(item.value for item in analysis.routes))

        expansion_started = perf_counter()
        activation: dict[NodeId, float] = defaultdict(float)
        paths: dict[NodeId, set[tuple[str, ...]]] = defaultdict(set)
        roots: dict[NodeId, set[NodeId]] = defaultdict(set)
        learned_association: dict[NodeId, float] = defaultdict(float)
        queue = deque()
        for entity_id in sorted(seeds, key=_key):
            activation[entity_id] += seeds[entity_id]
            roots[entity_id].add(entity_id)
            queue.append((entity_id, seeds[entity_id], 0, entity_id, frozenset((entity_id,)), ()))
        edges = 0
        missing_edges = 0
        while queue:
            current, magnitude, depth, root, visited, path = queue.popleft()
            if depth >= cfg.max_hops:
                continue
            neighbors: list[tuple[Association, NodeId]] = []
            for edge in self.memory.associations_for(current):
                other = edge.target_id if edge.source_id == current else edge.source_id
                if self.memory.exists(other):
                    if hasattr(self.memory,"lifecycle") and self.memory.lifecycle(other).state is not LifecycleState.ACTIVE: continue
                    neighbors.append((edge, other))
                else:
                    missing_edges += 1
            neighbors.sort(key=lambda pair: (-pair[0].strength if pair[0].strength is not None else -1.0,
                                             str(pair[0].id), _key(pair[1])))
            if len(neighbors) > cfg.max_fanout:
                truncated.add("fanout")
            selected = neighbors[:cfg.max_fanout]
            divisor = len(selected) if cfg.fanout_normalization and selected else 1
            for edge, other in selected:
                if edges >= cfg.max_edges:
                    truncated.add("edges")
                    queue.clear()
                    break
                edges += 1
                if other in visited:
                    continue
                base_strength = edge.strength if edge.strength is not None else 1.0
                base_strength = max(0.0, min(1.0, base_strength))
                adjustment = self.plasticity.association_adjustment(current, other)
                strength = max(0.0, min(1.0, base_strength + adjustment))
                propagated = magnitude * strength * cfg.hop_decay / divisor
                learned_association[other] += magnitude * (strength - base_strength) * cfg.hop_decay / divisor
                if propagated < cfg.minimum_activation:
                    continue
                if other not in activation and len(activation) >= cfg.max_candidates:
                    truncated.add("candidates")
                    continue
                activation[other] += propagated
                roots[other].add(root)
                next_path = (*path, str(edge.id))
                paths[other].add(next_path)
                found_by[other].add(RetrieverKind.ASSOCIATIVE.value)
                queue.append((other, propagated, depth + 1, root, visited | {other}, next_path))
        marks["expansion"] = (perf_counter() - expansion_started) * 1000

        scoring_started = perf_counter()
        weights = dict(cfg.weights)
        candidates = []
        now = cue.temporal_context
        query_now = utc_now()
        valid_at = cue.valid_at or query_now
        knowledge_at = cue.knowledge_at or query_now
        for entity_id in sorted(activation, key=_key):
            entity = self.memory.get(entity_id)
            if entity is None:
                continue
            provenance = getattr(entity, "provenance", None)
            source_id = provenance.source_id if provenance else entity.id if isinstance(entity, Source) else None
            truth = getattr(entity, "truth", None)
            provenance_valid = (provenance is None or self.memory.exists(provenance.source_id)
                                or truth is None or truth.recorded_at is None)
            if not provenance_valid:
                continue  # deterministic quarantine for orphan provenance
            contradiction = truth.contradiction if truth is not None else ContradictionKind.NONE
            newer_conflict = False
            if truth is not None:
                if not temporally_eligible(truth, valid_at=valid_at, knowledge_at=knowledge_at,
                                           current=cue.query_mode is QueryMode.CURRENT,
                                           superseded_by_other=bool(getattr(self.index, "is_superseded", lambda _: False)(entity_id))):
                    continue
                if cue.verification_policy is VerificationPolicy.VERIFIED_ONLY and truth.state is not TruthState.VERIFIED:
                    continue
                peer_ids = getattr(self.index, "truth_peers", lambda *_: ())(truth.fact_key, truth.context_key) if truth.fact_key else ()
                for other_id in peer_ids:
                    if other_id == entity_id: continue
                    other = self.memory.get(other_id)
                    other_truth = getattr(other, "truth", None)
                    if other_truth is not None:
                        if not temporally_eligible(other_truth, valid_at=valid_at, knowledge_at=knowledge_at,
                                                   current=cue.query_mode is QueryMode.CURRENT,
                                                   superseded_by_other=bool(getattr(self.index, "is_superseded", lambda _: False)(other.id))):
                            continue
                        detected = classify_disagreement(truth, other_truth)
                        if detected is ContradictionKind.CONTRADICTION:
                            contradiction = detected
                            state_rank = {TruthState.OBSERVED: 0, TruthState.ASSERTED: 1,
                                          TruthState.SUPPORTED: 2, TruthState.DISPUTED: 2,
                                          TruthState.VERIFIED: 3, TruthState.SUPERSEDED: -1,
                                          TruthState.INVALIDATED: -1}
                            newer_conflict = newer_conflict or bool(
                                other_truth.recorded_at and truth.recorded_at and
                                other_truth.recorded_at > truth.recorded_at and
                                state_rank[other_truth.state] >= state_rank[truth.state])
                if cue.query_mode is QueryMode.CURRENT and newer_conflict:
                    continue
            decision = authorize(getattr(entity, "security", None), cue.access_context)
            principal_keys = tuple(sorted(cue.access_context.principal.keys)) if cue.access_context and cue.access_context.principal else ()
            self.access_events.append(AccessAuditEvent(decision.code, principal_keys, entity_id,
                                                        cue.access_context.purpose if cue.access_context else None,
                                                        query_now))
            if not decision.allowed:
                continue
            if source_id is not None and self.materialization_check is not None:
                state = self.materialization_check(source_id)
                if state in ("PARTIAL_MEMORY", "MISSING_MEMORY"):
                    raise RetrievalError(RetrievalErrorCode.DEGRADED_MATERIALIZATION,
                                         f"source {source_id} has {state}")
            neighbor_context = bool(set(cue.context_ids) & roots[entity_id])
            if not neighbor_context and cue.context_ids:
                neighbor_context = any(
                    (edge.target_id if edge.source_id == entity_id else edge.source_id) in cue.context_ids
                    for edge in self.memory.associations_for(entity_id)
                )
            confidence_obj = getattr(entity, "confidence", None) or getattr(entity, "extraction_confidence", None)
            confidence = confidence_obj.value if confidence_obj is not None else None
            created = getattr(entity, "created_at", None) or getattr(entity, "registered_at", None)
            age_days = max(0.0, (now - created).total_seconds() / 86400) if now and created else None
            support = len(roots[entity_id] - {entity_id})
            pattern = cfg.pattern_bonus if entity_id not in seeds and support >= cfg.pattern_min_support else 0.0
            raw = {
                "seed": seeds.get(entity_id, 0.0),
                "activation": min(1.0, activation[entity_id]),
                "salience": min(1.0, len(reasons[entity_id]) / 2 + len(paths[entity_id]) / 4),
                "context": 1.0 if entity_id in cue.context_ids or neighbor_context or source_id in cue.source_ids else 0.0,
                "confidence": confidence if confidence is not None else 0.0,
                "recency": exp(-age_days / 365) if age_days is not None else 0.5,
                "provenance": 1.0 if provenance and provenance.locator else 0.5 if provenance else 0.0,
                "pattern": pattern,
            }
            if truth is not None and truth.recorded_at is not None and cue.verification_policy is VerificationPolicy.PREFER_VERIFIED:
                raw["confidence"] += 0.5 if truth.state is TruthState.VERIFIED else -0.25
            if contradiction is ContradictionKind.CONTRADICTION:
                # A conflict stays explicit; recency only orders the current-belief view.
                raw["confidence"] += 0.5 if not newer_conflict else -1.5
            components = tuple((name, raw[name] * weights[name]) for name in sorted(raw))
            channel_ranks = tuple(range(1, len(found_by[entity_id]) + 1))
            fusion_score = reciprocal_rank_fusion(channel_ranks) if channel_ranks else 0.0
            components += (("learned_association", learned_association[entity_id]),
                           ("learned_salience", self.plasticity.salience_adjustment(entity_id)),
                           ("learned_utility", self.plasticity.utility_adjustment(entity_id)))
            score = sum(value for _, value in components) + fusion_score * 5.0
            # Existing ActivationState is a request-local value; never stored.
            ActivationState(entity_id, activation[entity_id], utc_now(), str(request.request_id))
            candidates.append(RecallCandidate(
                entity_id, type(entity).__name__, 0, score, components, activation[entity_id],
                tuple(sorted(reasons[entity_id])), tuple(sorted(paths[entity_id]))[:cfg.max_edges],
                source_id, provenance.locator if provenance else None, confidence,
                tuple(sorted(lexical[entity_id])), support,
                truth.state if truth is not None else None, contradiction, True, provenance_valid,
                decision.code,
                tuple(sorted(found_by[entity_id])), fusion_score,
            ))
        if cue.verification_policy is VerificationPolicy.PREFER_VERIFIED:
            verified_keys = {getattr(self.memory.get(item.entity_id), "truth", None).fact_key
                             for item in candidates
                             if getattr(self.memory.get(item.entity_id), "truth", None) is not None
                             and getattr(self.memory.get(item.entity_id), "truth").state is TruthState.VERIFIED
                             and getattr(self.memory.get(item.entity_id), "truth").fact_key}
            candidates = [item for item in candidates if not (
                getattr(self.memory.get(item.entity_id), "truth", None) is not None
                and getattr(self.memory.get(item.entity_id), "truth").fact_key in verified_keys
                and getattr(self.memory.get(item.entity_id), "truth").state is not TruthState.VERIFIED)]
        candidates.sort(key=lambda item: (-item.score, _key(item.entity_id)))
        limit = min(request.max_results or cfg.max_results, cfg.max_results)
        if len(candidates) > limit:
            truncated.add("results")
        ranked = tuple(RecallCandidate(item.entity_id, item.entity_type, rank, item.score,
                                       item.components, item.activation, item.seed_reasons,
                                       item.association_paths, item.source_id, item.locator,
                                       item.confidence, item.lexical_tokens, item.pattern_support,
                                       item.truth_state, item.contradiction, item.temporally_valid,
                                       item.provenance_valid, item.authorization, item.found_by, item.fusion_score)
                       for rank, item in enumerate(candidates[:limit], 1))
        if cfg.source_diversity:
            selected = []
            seen = set()
            for item in ranked:
                if item.source_id not in seen:
                    selected.append(item)
                    seen.add(item.source_id)
                    if len(selected) == cfg.working_memory_capacity: break
            for item in ranked:
                if len(selected) == cfg.working_memory_capacity: break
                if item not in selected: selected.append(item)
            working = tuple(selected)
        else:
            working = ranked[:cfg.working_memory_capacity]
        # Context optimization is non-destructive: candidates remain explainable, while
        # model-visible working memory suppresses exact duplicates and weak tail items.
        optimized_working = []
        seen_text = set()
        threshold = working[0].score * 0.55 if working else 0.0
        for item in working:
            entity = self.memory.get(item.entity_id)
            body = (getattr(entity, "content", None) or getattr(entity, "statement", None)
                    or getattr(entity, "label", None) or getattr(entity, "description", None))
            normalized_body = " ".join(body.casefold().split()) if body else None
            if normalized_body and normalized_body in seen_text: continue
            if item.score < threshold and RetrieverKind.ASSOCIATIVE.value not in item.found_by: continue
            optimized_working.append(item)
            if normalized_body: seen_text.add(normalized_body)
        working = tuple(optimized_working)
        marks["scoring"] = (perf_counter() - scoring_started) * 1000
        return RecallResult(request.request_id, ranked, working,
                            (("seeds", len(seeds)), ("candidates", len(activation)),
                             ("edges", edges), ("missing_edges", missing_edges),
                             ("generated_candidates", getattr(self.index, "generated_candidates", len(seeds))),
                             ("ranked_candidates", getattr(self.index, "ranked_candidates", len(seeds))),
                             ("returned", len(ranked))),
                            (("seed", marks["seed"]), ("expansion", marks["expansion"]),
                             ("scoring", marks["scoring"]), ("total", (perf_counter() - started) * 1000)),
                            tuple(sorted(truncated)), cfg.version,
                            "SUFFICIENT_EVIDENCE" if ranked else "INSUFFICIENT_EVIDENCE",
                            tuple(item.value for item in analysis.routes))
