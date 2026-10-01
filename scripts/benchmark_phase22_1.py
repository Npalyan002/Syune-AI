import json
from pathlib import Path
from benchmarks.phase22_1 import run
result=run(); target=Path("docs/evals/phase22_1/post/POST_REMEDIATION_SCALE_V2.json")
target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(target)
