"""Frozen Phase 28R.1 command-line entrypoint."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.phase28r1_execution import main

if __name__ == "__main__":
    raise SystemExit(main())
