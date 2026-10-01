from pathlib import Path
import json
from benchmarks.phase25_5 import write_results

if __name__ == "__main__":
    print(json.dumps(write_results(Path("docs/evals/phase25_5")),indent=2))
