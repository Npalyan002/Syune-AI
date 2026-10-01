"""PHASE 14 bounded local benchmark/soak harness; synthetic fixtures only."""
import argparse
from contextlib import ExitStack
from dataclasses import asdict
import gc
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
from time import perf_counter, process_time
import tracemalloc
from uuid import UUID
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests/phase14'))
from scenario import pipeline, bind_sandbox
from syune.core import *
from syune.memory import SQLiteMemoryRepository, Source, Observation, Provenance, Association
from syune.retrieval import InvertedSeedIndex, RetrievalService, RecallCue, RecallRequest
from syune.cognition import CognitiveService, CognitiveRequest, ProfileRegistry, ProfileName
from syune.council import CouncilService, CouncilRequest, CouncilMemberSpec
from syune.executive import ExecutiveService, ExecutiveRequest, Goal, GoalSource, RuntimeResultStatus
from syune.evals.metrics import percentiles
from syune.evals.invariants import audit
from syune.evals.model import Health


def resources():
    result = {'cpu_seconds':process_time()}
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in ('peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        handle = kernel.GetCurrentProcess()
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        kernel.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        info = Counters(); info.cb = ctypes.sizeof(info)
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle,ctypes.byref(info),info.cb):
            result.update(rss_bytes=info.rss,peak_rss_bytes=info.peak_rss)
        count = wintypes.DWORD()
        if kernel.GetProcessHandleCount(handle,ctypes.byref(count)): result['handles']=count.value
    return result


def samples(call, repeats):
    values=[]; result=None
    for _ in range(repeats):
        tick=perf_counter();result=call();values.append((perf_counter()-tick)*1000)
    return percentiles(values), result


def scale(size, repeats, root):
    path=root/f'memory-{size}.sqlite3'; at=datetime(2026,1,1,tzinfo=timezone.utc)
    sid=SourceId(UUID(int=1));p=Provenance(ProvenanceId(UUID(int=2)),sid,at)
    tick=perf_counter()
    with SQLiteMemoryRepository(path) as memory:
        memory.put(Source(sid,'synthetic','scale fixture',at))
        for start in range(0,size,1000):
            memory.put_many(tuple(Observation(ObservationId(UUID(int=n+100)),f'unique{n} amber evidence' if n<2 else f'distractor{n}', 'text',p,at,at) for n in range(start,min(size,start+1000))))
        memory.add_association(Association(AssociationId(UUID(int=3)),ObservationId(UUID(int=100)),ObservationId(UUID(int=101)),'supports',p,Confidence(.5),at,.6))
        build_ms=(perf_counter()-tick)*1000
        tick=perf_counter();index=InvertedSeedIndex(memory);index.rebuild();index_ms=(perf_counter()-tick)*1000
        service=RetrievalService(memory,index);request=RecallRequest(RecallCue(text='unique0'))
        cold,_=samples(lambda:service.recall(request),1)
        recall,last=samples(lambda:service.recall(request),repeats)
        assert ObservationId(UUID(int=100)) in {x.entity_id for x in last.candidates}
        result={'entities':size,'build_ms':build_ms,'index_build_ms':index_ms,'first_recall':cold,'warm_recall':recall,
            'index_text_bytes':sum(len(x.text.encode()) for x in index.entries.values()),'db_bytes':path.stat().st_size,'resources':resources()}
        if size <= 10000:
            cognitive=CognitiveService(memory,service)
            cr=CognitiveRequest(CognitiveRequestId.new(),entity_ids=(ObservationId(UUID(int=100)),ObservationId(UUID(int=101))))
            result['cognition'],cog=samples(lambda:cognitive.process(cr),5)
            profiles=ProfileRegistry();members=tuple(CouncilMemberSpec(profiles.by_name(x).id) for x in (ProfileName.GENERAL,ProfileName.SYSTEMS))
            request=CouncilRequest(CouncilRequestId.new(),cr,members)
            result['council'],council=samples(lambda:CouncilService(cognitive).run(request),3)
            goal=Goal(GoalId.new(),'update sandbox file',('review complete',),source=GoalSource.TEST)
            result['planning'],planned=samples(lambda:ExecutiveService().plan(ExecutiveRequest(ExecutiveRequestId.new(),goal,cog,council)),10)
            result['planning_status']=planned.status.value
    tick=perf_counter()
    with SQLiteMemoryRepository(path) as memory:
        open_ms=(perf_counter()-tick)*1000;tick=perf_counter();index=InvertedSeedIndex(memory);index.rebuild()
        result['restart_open_ms']=open_ms;result['restart_rebuild_ms']=(perf_counter()-tick)*1000
    return result


def soak(seconds, root, output):
    start=perf_counter();before=resources();latencies=[];stages={};errors=[];cycle=0;snapshots=[]
    while perf_counter()-start<seconds:
        tick=perf_counter()
        with tempfile.TemporaryDirectory(dir=root) as temp, ExitStack() as stack:
            c=bind_sandbox(pipeline(Path(temp),stack));stack.callback(c['execution_store'].close)
            result=c['runtime'].execute_approved(c['execution_request'])
            assert result.status is RuntimeResultStatus.COMPLETED_VERIFIED
            again=c['runtime'].execute_approved(c['execution_request'])
            assert c['adapter'].calls==1 and again.receipts[0].idempotent_replay
            checked=audit(c['memory'],c['registry'],c['learning'],(c['execution_plan'],),c['execution_store'])
            assert checked.health is Health.HEALTHY,checked.issues
            assert c['learning'].count_signals()==0
            for name,value in result.timings_ms:stages.setdefault('execution_'+name,[]).append(value)
            for name,value in c['cognitive'].timings_ms:stages.setdefault('cognition_'+name,[]).append(value)
            stages.setdefault('council',[]).append(c['council'].diagnostics.total_ms)
            stages.setdefault('planning',[]).append(dict(c['planned'].diagnostics.timings_ms)['total'])
        cycle+=1;latencies.append((perf_counter()-tick)*1000)
        if cycle%25==0:
            gc.collect();snapshots.append({'cycle':cycle,'elapsed_seconds':perf_counter()-start,**resources()})
            output.write_text(json.dumps({'status':'RUNNING','cycles':cycle,'elapsed_seconds':perf_counter()-start,'resources':snapshots[-1]},indent=2))
    gc.collect();after=resources()
    return {'status':'PASS','duration_seconds':perf_counter()-start,'cycles':cycle,'errors':errors,'before':before,'after':after,
        'snapshots':snapshots,'latency':percentiles(latencies),'first_quarter':percentiles(latencies[:max(1,len(latencies)//4)]),
        'last_quarter':percentiles(latencies[-max(1,len(latencies)//4):]),'stages':{k:percentiles(v) for k,v in stages.items()},
        'limitations':['connection churn soak; shared long-lived writer concurrency unsupported','RSS is process working set; allocator/OS caching is platform dependent']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['scale','soak']);parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--sizes',type=int,nargs='+',default=[100,1000,10000,50000,100000]);parser.add_argument('--repeats',type=int,default=20)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if not 1<=args.seconds<=1800 or not 1<=args.repeats<=100 or any(not 100<=s<=100000 for s in args.sizes):parser.error('bounded local workload required')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    work=ROOT/'.syune/phase14-runs';work.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as temp:
        if args.mode=='scale':
            results=[]
            for size in args.sizes:
                results.append(scale(size,args.repeats,Path(temp)))
                args.output.write_text(json.dumps({'status':'RUNNING','results':results},indent=2))
            result={'status':'PASS','results':results}
        else:result=soak(args.seconds,Path(temp),args.output)
    result.update(python=platform.python_version(),platform=platform.platform())
    args.output.write_text(json.dumps(result,indent=2));print(json.dumps({'status':result['status'],'output':str(args.output)}))

if __name__=='__main__': main()
