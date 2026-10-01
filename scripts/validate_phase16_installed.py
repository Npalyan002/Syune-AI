"""Validate the Phase 16 SDK and MCP from an installed wheel outside the checkout."""
import argparse, asyncio, json, os, subprocess, tempfile
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters


TOOLS={"syune_health","syune_status","syune_capabilities","syune_source_status","syune_memory_get",
       "syune_recall","syune_cognize","syune_council","syune_plan","syune_study_source"}


def run(*args,env=None,cwd=None):
    return subprocess.run([str(x) for x in args],capture_output=True,text=True,check=True,env=env,cwd=cwd,timeout=90).stdout.strip()


async def mcp(executable,state,library,source):
    env=os.environ.copy();env["SYUNE_STATE_ROOT"]=str(state);env["SYUNE_STUDY_ROOTS"]=str(library)
    params=StdioServerParameters(command=str(executable),args=["mcp","serve"],env=env,cwd=str(library))
    async with Client(params) as client:
        tools={x.name for x in (await client.list_tools()).tools}; assert tools==TOOLS
        health=(await client.call_tool("syune_health")).structured_content
        await client.call_tool("syune_study_source",{"path":str(source)})
        recall=(await client.call_tool("syune_recall",{"text":"installed phase sixteen"})).structured_content
        cognition=(await client.call_tool("syune_cognize",{"text":"installed phase sixteen"})).structured_content
        council=(await client.call_tool("syune_council",{"text":"installed phase sixteen"})).structured_content
        plan=(await client.call_tool("syune_plan",{"goal":"review installed phase sixteen"})).structured_content
    assert health["public_api_version"]=="1" and recall["candidates"]
    assert cognition["version"]=="1" and council["agreement_meaning"] and plan["execution_authority"] is False
    return sorted(tools)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--python",type=Path,required=True);parser.add_argument("--syune",type=Path,required=True)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);state=root/"state";library=root/"library";library.mkdir();source=library/"fixture.txt"
        source.write_text("installed phase sixteen with provenance",encoding="utf-8")
        env=os.environ.copy();env["SYUNE_STUDY_ROOTS"]=str(library)
        run(args.syune,"init","--state-root",state,"--json",env=env,cwd=library)
        code=("import json,sys; from syune import Syune,StudyRequest,RecallRequest,CognitiveRequest,CouncilRequest,PlanRequest; "
              "b=Syune.open(state_root=sys.argv[1]); h=b.handshake(['1']); s=b.study(StudyRequest(sys.argv[2])); "
              "r=b.recall(RecallRequest(cue='installed phase sixteen')); c=b.cognize(CognitiveRequest(cue='installed phase sixteen')); "
              "u=b.council(CouncilRequest('installed phase sixteen')); p=b.plan(PlanRequest('review installed phase sixteen')); "
              "print(json.dumps({'version':h.selected_version,'studied':s.data['is_studied'],'recalled':bool(r.data['candidates']),"
              "'cognition':c.data['version'],'council':u.data['status'],'plan':p.data['status']})); b.close()")
        sdk=json.loads(run(args.python,"-c",code,state,source,env=env,cwd=library))
        tools=asyncio.run(mcp(args.syune,state,library,source))
        assert sdk["version"]=="1" and sdk["studied"] and sdk["recalled"]
        print(json.dumps({"status":"PASS","sdk":sdk,"mcp_tools":tools},sort_keys=True))


if __name__=="__main__": main()
