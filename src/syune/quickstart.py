"""Packaged executable example for the Lean v1 quickstart."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from syune import ContextRequest, ProvenanceMode, RecallRequest, ReviseRequest, Syune, TypedId

def emit(name, value): print(json.dumps({name: value.data}, default=str, sort_keys=True))

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--state-root",required=True); args=parser.parse_args(argv)
    with Syune.open(state_root=args.state_root) as syune:
        remembered=syune.remember("The release channel is amber."); emit("remember",remembered)
        old_id=remembered.data["memory_id"]
        emit("context",syune.context(ContextRequest("release channel",provenance_mode=ProvenanceMode.FULL)))
        before=datetime.now(timezone.utc).isoformat()
        revised=syune.revise(ReviseRequest(TypedId.parse(old_id),"The release channel is green.")); emit("revise",revised)
        emit("current",syune.recall(RecallRequest("release channel",query_mode="CURRENT")))
        emit("historical",syune.recall(RecallRequest("release channel",query_mode="AS_OF",valid_at=before,knowledge_at=before)))
        emit("history",syune.history(revised.data["memory_id"])); emit("archive",syune.archive(old_id)); emit("audit",syune.audit())
    with Syune.open(state_root=args.state_root) as syune: emit("restart",syune.recall("release channel"))

if __name__=="__main__": main()
