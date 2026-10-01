"""SQLite execution metadata; transactions never cover the external side effect."""
import json
import sqlite3
from hashlib import sha256
from datetime import datetime
from pathlib import Path
from syune.core import *
from .model import PlanId, ActionProposalId
from .runtime_model import *


class SQLiteExecutionRepository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        try:
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1): raise ValueError('incompatible execution schema')
            tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables and tables != {'executions'}: raise ValueError('unrecognized execution schema')
            self.db.execute('CREATE TABLE IF NOT EXISTS executions (idempotency_key TEXT PRIMARY KEY, state TEXT NOT NULL, payload TEXT NOT NULL, invocation TEXT NOT NULL)')
            columns = tuple(r[1] for r in self.db.execute('PRAGMA table_info(executions)'))
            if columns != ('idempotency_key','state','payload','invocation'): raise ValueError('invalid execution columns')
            # Explicit compatibility adoption of the exact Phase 13 schema; no data rewriting.
            for (key,) in tuple(self.db.execute('SELECT idempotency_key FROM executions')): self.row(key)
            self.db.execute('PRAGMA user_version=1')
            self.db.commit()
        except Exception:
            self.db.close()
            raise

    def close(self): self.db.close()

    def row(self, key):
        row = self.db.execute('SELECT state,payload,invocation FROM executions WHERE idempotency_key=?',(key,)).fetchone()
        if row is None: return None
        try:
            state, payload, invocation = IdempotencyState(row[0]), json.loads(row[1]), json.loads(row[2])
            ExecutionId.parse(payload['execution_id'])
            PlanId.parse(payload['plan_id'])
            pid = ActionProposalId.parse(payload['proposal_id'])
            CapabilityId.parse(invocation['capability_id'])
            if str(pid) != invocation['proposal_id']: raise ValueError('proposal identity mismatch')
            if type(payload['plan_version']) is not int or payload['plan_version'] < 1: raise ValueError('invalid version')
            SideEffectClass(invocation['side_effect'])
            pairs = invocation['parameters']
            if not isinstance(pairs, list) or any(not isinstance(p,list) or len(p)!=2 or any(type(x) is not str for x in p) for p in pairs): raise ValueError('invalid parameters')
            if len(dict(pairs)) != len(pairs): raise ValueError('duplicate parameter')
            material=(PlanId.parse(payload['plan_id']),payload['plan_version'],pid,CapabilityId.parse(invocation['capability_id']),tuple(map(tuple,pairs)))
            if sha256(repr(material).encode()).hexdigest()!=key: raise ValueError('invocation fingerprint mismatch')
            if state in (IdempotencyState.SUCCEEDED,IdempotencyState.ROLLED_BACK,IdempotencyState.FAILED_FINAL) and 'receipt_id' not in payload: raise ValueError('terminal receipt missing')
            if state is IdempotencyState.SUCCEEDED and payload.get('status') != ExecutionStatus.SUCCEEDED_VERIFIED.value: raise ValueError('state/receipt mismatch')
            return state, payload, invocation
        except (ValueError,TypeError,KeyError) as exc:
            raise ValueError('corrupt execution record') from exc

    def state(self, key):
        row = self.row(key)
        return row[0] if row else IdempotencyState.NOT_SEEN

    def begin(self, key, payload, invocation):
        # Claim atomically. Never overwrite a completed or uncertain attempt.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            prior = self.state(key)
            identity = self.db.execute("SELECT idempotency_key FROM executions WHERE json_extract(payload,'$.execution_id')=?",(payload['execution_id'],)).fetchone()
            if identity and identity[0]!=key:raise ValueError('execution identity already exists under another key')
            values = (IdempotencyState.IN_PROGRESS.value,json.dumps(payload,sort_keys=True),json.dumps(invocation,sort_keys=True),key)
            if prior is IdempotencyState.NOT_SEEN:
                self.db.execute('INSERT INTO executions(state,payload,invocation,idempotency_key) VALUES(?,?,?,?)', values)
            elif prior is IdempotencyState.FAILED_RETRYABLE:
                self.db.execute('UPDATE executions SET state=?,payload=?,invocation=? WHERE idempotency_key=?', values)
            else:
                raise ValueError('execution already claimed; reconcile before retry')

    def finish(self, key, state, payload):
        with self.db:
            prior = self.row(key)
            if prior is None: raise ValueError('execution record missing')
            # Retain audit material across both receipt commits and reconciliation.
            merged = dict(prior[1])
            merged.update(payload)
            self.db.execute('UPDATE executions SET state=?,payload=? WHERE idempotency_key=?',
                (state.value,json.dumps(merged,sort_keys=True),key))

    def incomplete(self):
        keys = tuple(r[0] for r in self.db.execute('SELECT idempotency_key FROM executions WHERE state IN (?,?)',
            (IdempotencyState.IN_PROGRESS.value,IdempotencyState.UNKNOWN_OUTCOME.value)))
        return tuple((key,self.row(key)[1],self.row(key)[2]) for key in keys)

    def receipt(self, key, replay=False):
        row = self.row(key)
        if not row or 'receipt_id' not in row[1]: return None
        _, p, _ = row
        out = ver = None
        if p.get('outcome'):
            o = p['outcome']
            out = ExecutionOutcome(o['status'],o['effect'],tuple(map(tuple,o['data'])),o['confirmed'],o['target'],
                tuple(map(tuple,o['adapter'])),tuple(o['warnings']),tuple(o['uncertainty']),VerificationMode(o['mode']))
        if p.get('verification'):
            v = p['verification']
            ver = VerificationResult(VerificationId.parse(v['id']),VerificationStatus(v['status']),VerificationMode(v['mode']),v['expected'],v['observed'],tuple(v['reasons']))
        return ExecutionReceipt(ExecutionReceiptId.parse(p['receipt_id']),ExecutionId.parse(p['execution_id']),PlanId.parse(p['plan_id']),
            p['plan_version'],ActionProposalId.parse(p['proposal_id']),ExecutionStatus(p['status']),out,ver,replay,datetime.fromisoformat(p['created_at']))

def receipt_payload(receipt):
    o=receipt.outcome;v=receipt.verification
    return {"receipt_id":str(receipt.id),"execution_id":str(receipt.execution_id),"plan_id":str(receipt.plan_id),"plan_version":receipt.plan_version,"proposal_id":str(receipt.proposal_id),"status":receipt.status.value,"created_at":receipt.created_at.isoformat(),"outcome":None if not o else {"status":o.status,"effect":o.observed_effect,"data":o.output_data,"confirmed":o.side_effect_confirmed,"target":o.target_identity,"adapter":o.adapter_metadata,"warnings":o.warnings,"uncertainty":o.uncertainty,"mode":o.verification_requirement.value},"verification":None if not v else {"id":str(v.id),"status":v.status.value,"mode":v.mode.value,"expected":v.expected,"observed":v.observed,"reasons":v.reasons}}
def attach_record(payload,record):
    payload["record"]={"execution_id":str(record.id),"request_id":str(record.request_id),"plan_id":str(record.plan_id),"plan_version":record.plan_version,"proposal_id":str(record.proposal_id),"capability_id":str(record.capability_id),"capability_version":record.capability_version,"approval_id":str(record.approval_id),"approval_fingerprint":record.approval_fingerprint,"invocation_fingerprint":record.invocation_fingerprint,"gate_outcome":record.gate.outcome.value,"gate_rules":record.gate.rule_ids,"started_at":record.started_at.isoformat(),"completed_at":record.completed_at.isoformat() if record.completed_at else None,"status":record.status.value,"retry_count":record.retry_count,"rollback_status":record.rollback_status.value if record.rollback_status else None,"error_code":record.error_code,"error_message":record.error_message,"idempotency_key":record.idempotency_key};return payload
