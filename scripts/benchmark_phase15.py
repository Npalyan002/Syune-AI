"""Installed-command bootstrap measurements for the Phase 15 local baseline."""
import argparse,json,subprocess
from pathlib import Path
from statistics import median
from time import perf_counter


def measure(executable,args,repeats=5):
    values=[]
    for _ in range(repeats):
        tick=perf_counter();subprocess.run([str(executable),*args],capture_output=True,text=True,check=True,timeout=60)
        values.append((perf_counter()-tick)*1000)
    values.sort()
    return {'p50_ms':median(values),'p95_ms':values[-1],'p99_ms':values[-1],'samples':len(values)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--syune',type=Path,required=True);parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    subprocess.run([str(args.syune),'init','--state-root',str(args.state_root),'--json'],check=True,capture_output=True,text=True,timeout=60)
    result={'status':'PASS','version_process':measure(args.syune,['--version']),
        'status_process':measure(args.syune,['status','--state-root',str(args.state_root),'--json']),
        'health_process':measure(args.syune,['health','--state-root',str(args.state_root),'--json']),
        'notes':['fresh process timings on installed Windows wheel','p95/p99 are maxima of five samples; not production tail estimates']}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
