from __future__ import annotations

import json
from pathlib import Path
from benchmarks.phase22 import run


def main() -> None:
    result = run()
    target = Path("docs/evals/phase22/post/POST_PHASE_22_SCALE.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__": main()
