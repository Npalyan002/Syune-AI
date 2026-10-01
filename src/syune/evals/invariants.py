"""Read-only cross-store invariant audit. Diagnostics contain IDs/codes, never raw content."""
from dataclasses import dataclass
import json
from math import isfinite
from syune.core import ObservationId, MemoryTraceId
from syune.memory import Source, Observation, MemoryTrace, Evidence
from syune.study.model import SourceRevisionId
from syune.perception.model import RunStatus, Modality, RepresentationType, PerceptionMethod
from .model import Health


@dataclass(frozen=True)
class AuditResult:
    health: Health
    issues: tuple[str, ...]
    checked: tuple[tuple[str, int], ...]


def audit(memory, registry=None, learning=None, plans=(), executions=None, overlay_bound=.5):
    issues, counts = [], []
    try:
        entities = memory.iter_entities()
        ids = {x.id for x in entities}
        if len(ids) != len(entities): issues.append('memory:duplicate_identity')
        provenance_ids = {x.provenance.id for x in entities if hasattr(x, 'provenance')}
        edges = {}
        for item in entities:
            if item.schema_version != '1': issues.append('memory:schema_version')
            provenance = getattr(item, 'provenance', None)
            if provenance:
                if provenance.source_id not in ids: issues.append('memory:source_missing')
                if not set(provenance.parent_provenance_ids) <= provenance_ids: issues.append('memory:parent_provenance_missing')
            if isinstance(item, MemoryTrace) and item.entity_id not in ids: issues.append('memory:trace_target_missing')
            if isinstance(item, Evidence) and not set(item.claim_ids) <= ids: issues.append('memory:claim_missing')
            for edge in memory.associations_for(item.id): edges[edge.id] = edge
        for edge in edges.values():
            if edge.source_id not in ids or edge.target_id not in ids: issues.append('memory:association_endpoint_missing')
            if edge.provenance.source_id not in ids: issues.append('memory:association_source_missing')
        counts.extend((('memory_entities', len(entities)), ('associations', len(edges))))
    except Exception as exc:
        issues.append('memory:decode:' + type(exc).__name__)
        entities, ids = (), set()
    if registry is not None:
        try:
            rows = registry._db.execute('SELECT revision_id FROM revisions').fetchall()
            revisions = {r[0]: registry.status(SourceRevisionId.parse(r[0])) for r in rows}
            seen = {}
            for rid, status in revisions.items():
                if len(status.sha256) != 64 or any(c not in '0123456789abcdef' for c in status.sha256): issues.append('study:hash_invalid')
                owner = seen.setdefault(status.sha256, status.source_id)
                if owner != status.source_id: issues.append('study:duplicate_canonical_source')
                if status.previous_revision_id and str(status.previous_revision_id) not in revisions: issues.append('study:revision_lineage_missing')
                if status.source_id not in ids: issues.append('study:source_missing')
                if status.is_studied and status.blocks_encoded != status.blocks_total: issues.append('study:materialization_count')
                for n, value in enumerate(status.derived_memory_ids):
                    mid = ObservationId.parse(value) if n % 2 == 0 else MemoryTraceId.parse(value)
                    item = memory.get(mid)
                    if item is None:
                        issues.append('study:materialization_missing')
                    elif item.provenance.source_id != status.source_id or item.provenance.source_version_id != status.source_version_id:
                        issues.append('study:materialization_provenance')
            runs = {r[0]: r for r in registry._db.execute('SELECT run_id,revision_id,status FROM perception_runs')}
            for rid, revision, state in runs.values():
                RunStatus(state)
                if revision not in revisions: issues.append('perception:revision_missing')
            segments = {r[0]: r for r in registry._db.execute('SELECT segment_id,run_id,fingerprint,modality,representation,locator,method FROM perception_segments')}
            for sid, run, fingerprint, modality, representation, locator, method in segments.values():
                Modality(modality); RepresentationType(representation); PerceptionMethod(method)
                if run not in runs or len(fingerprint) != 64 or not locator: issues.append('perception:invalid_segment')
            for item in entities:
                if not isinstance(item, Observation): continue
                process = item.provenance.process_id or ''
                if process.startswith('study:perception:'):
                    _, _, run, segment, method = process.split(':', 4)
                    row = segments.get(segment)
                    if row is None or row[1] != run or row[6] != method:
                        issues.append('provenance:segment_edge_broken')
                    elif revisions[runs[run][1]].source_version_id != item.provenance.source_version_id:
                        issues.append('provenance:revision_edge_broken')
            counts.extend((('source_revisions', len(revisions)), ('perceived_segments', len(segments))))
            if registry._db.execute('PRAGMA foreign_key_check').fetchall(): issues.append('study:foreign_key')
        except Exception as exc:
            issues.append('study:decode:' + type(exc).__name__)
    if learning is not None:
        try:
            states = learning.snapshot()
            for state in states:
                if state.schema_version != '1': issues.append('learning:schema_version')
                if any(not isfinite(v) or abs(v) > overlay_bound for v in (state.utility_delta, state.salience_delta, state.association_delta)):
                    issues.append('learning:overlay_bounds')
            counts.append(('overlay_states', len(states)))
        except Exception as exc:
            issues.append('learning:decode:' + type(exc).__name__)
    plan_map = {(p.id, p.version): p for p in plans}
    for plan in plans:
        steps = {s.id for s in plan.steps}
        if not set(plan.entity_ids) <= ids: issues.append('plan:evidence_missing')
        for step in plan.steps:
            if not set(step.dependencies) <= steps: issues.append('plan:dependency_missing')
            for proposal in step.action_proposals:
                if proposal.step_id != step.id: issues.append('plan:proposal_step_mismatch')
                if not set(proposal.entity_ids) <= ids: issues.append('plan:proposal_evidence_missing')
    if executions is not None:
        try:
            rows = executions.db.execute('SELECT idempotency_key FROM executions').fetchall()
            seen = set()
            for (key,) in rows:
                state, payload, invocation = executions.row(key)
                receipt = executions.receipt(key) if 'receipt_id' in payload else None
                if receipt:
                    if receipt.execution_id in seen: issues.append('execution:duplicate_execution_id')
                    seen.add(receipt.execution_id)
                    plan = plan_map.get((receipt.plan_id, receipt.plan_version))
                    if plan is None: issues.append('execution:plan_missing')
                    elif receipt.proposal_id not in {p.id for s in plan.steps for p in s.action_proposals}: issues.append('execution:proposal_missing')
                    record = payload.get('record')
                    if not record or not record.get('approval_id') or not record.get('approval_fingerprint'):
                        issues.append('execution:approval_audit_missing')
            counts.append(('execution_records', len(rows)))
        except Exception as exc:
            issues.append('execution:decode:' + type(exc).__name__)
    return AuditResult(Health.UNHEALTHY if issues else Health.HEALTHY, tuple(sorted(set(issues))), tuple(counts))
