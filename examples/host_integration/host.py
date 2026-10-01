"""Generic host using only the documented top-level public API."""
from pathlib import Path
import argparse

from syune import CognitiveRequest, CouncilRequest, PlanRequest, RecallRequest, StudyRequest, Syune


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    with Syune.open(state_root=args.state_root) as brain:
        print(brain.handshake(["1"]))
        print(brain.health())
        print(brain.study(StudyRequest(str(args.source))))
        print(brain.recall(RecallRequest(cue="key evidence")))
        print(brain.cognize(CognitiveRequest(cue="assess key evidence")))
        print(brain.council(CouncilRequest("assess key evidence", ("GENERAL", "RESEARCH"))))
        print(brain.plan(PlanRequest("review the evidence", ("review is documented",))))


if __name__ == "__main__": main()
