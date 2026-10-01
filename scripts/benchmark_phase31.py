"""Prepare, traverse, execute and analyze the frozen Phase 31 experiment."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks.phase31 import freeze
from benchmarks.phase31_execution import Runner
from benchmarks.phase31_reporting import analyze

def main():
 p=argparse.ArgumentParser();p.add_argument("mode",choices=("freeze","fake","live","analyze"));p.add_argument("--out",type=Path,default=Path("docs/phase31/evidence/live_v1"));a=p.parse_args()
 if a.mode=="freeze": result=freeze(a.out/"freeze")
 elif a.mode in ("fake","live"):
  freeze(a.out/"freeze");runner=Runner(a.out,a.mode=="live")
  try:result=runner.run()
  finally:runner.close()
 else:result=analyze(a.out,a.out.parent.parent)
 print(json.dumps(result,indent=2))
if __name__=="__main__":main()
