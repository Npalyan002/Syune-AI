"""Fresh interpreter cold-start measurement over a persisted deterministic Study fixture."""
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/phase14'))
from scenario import pipeline
code='''
from time import perf_counter
started=perf_counter()
import json,sys
from pathlib import Path
from syune.core import CognitiveRequestId
from syune.memory import SQLiteMemoryRepository
from syune.retrieval import InvertedSeedIndex,RetrievalService,RecallRequest,RecallCue
from syune.cognition import CognitiveService,CognitiveRequest
imports=(perf_counter()-started)*1000
started=perf_counter()
with SQLiteMemoryRepository(Path(sys.argv[1])) as memory:
    opened=(perf_counter()-started)*1000
    tick=perf_counter();index=InvertedSeedIndex(memory);index.rebuild();rebuilt=(perf_counter()-tick)*1000
    retrieval=RetrievalService(memory,index);tick=perf_counter();retrieval.recall(RecallRequest(RecallCue(text='Amber')));recalled=(perf_counter()-tick)*1000
    tick=perf_counter();CognitiveService(memory,retrieval).process(CognitiveRequest(CognitiveRequestId.new(),text='Amber'));cognitive=(perf_counter()-tick)*1000
print(json.dumps(dict(import_ms=imports,repository_open_ms=opened,index_rebuild_ms=rebuilt,first_recall_ms=recalled,first_cognitive_ms=cognitive)))
'''
with tempfile.TemporaryDirectory(dir=ROOT/'.syune/phase14-runs') as directory:
    with ExitStack() as stack:pipeline(Path(directory),stack)
    results=[]
    for _ in range(5):
        tick=perf_counter();output=subprocess.run([sys.executable,'-c',code,str(Path(directory)/'memory.sqlite3')],capture_output=True,text=True,check=True,timeout=30)
        item=json.loads(output.stdout);item['process_total_ms']=(perf_counter()-tick)*1000;results.append(item)
(ROOT/'.syune/phase14-cold.json').write_text(json.dumps({'runs':results,'dataset':'one studied text, two observations, two traces, one relation'},indent=2))
print('cold-start measurements complete')
