"""Validate an installed wheel from outside the repository using the official MCP client."""
import argparse,asyncio,json,os,subprocess,tempfile
from pathlib import Path
from time import perf_counter
from mcp import Client
from mcp.client.stdio import StdioServerParameters


def command(executable,*args,env=None):
    tick=perf_counter();result=subprocess.run([str(executable),*map(str,args)],capture_output=True,text=True,
        check=True,env=env,timeout=60)
    return result.stdout.strip(),(perf_counter()-tick)*1000


def payload(result):
    assert not result.is_error and result.structured_content is not None,result.content
    return result.structured_content


async def mcp_check(executable,state,library,source):
    env=os.environ.copy();env['SYUNE_STATE_ROOT']=str(state);env['SYUNE_STUDY_ROOTS']=str(library)
    params=StdioServerParameters(command=str(executable),args=['mcp','serve','--state-root',str(state)],env=env,cwd=str(library))
    tick=perf_counter()
    async with Client(params) as client:
        tools={x.name for x in (await client.list_tools()).tools}
        health=payload(await client.call_tool('syune_health'))
        startup=(perf_counter()-tick)*1000
        studied=payload(await client.call_tool('syune_study_source',{'path':str(source)}))
        tick=perf_counter();recall=payload(await client.call_tool('syune_recall',{'text':'installed portability marker'}))
        first_recall=(perf_counter()-tick)*1000
    return tools,health,studied,recall,startup,first_recall


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--syune',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);state=root/'state';library=root/'library';library.mkdir();source=library/'source.txt'
        source.write_text('installed portability marker',encoding='utf-8')
        version,version_ms=command(args.syune,'--version')
        first,init_ms=command(args.syune,'init','--state-root',state,'--json')
        second,reinit_ms=command(args.syune,'init','--state-root',state,'--json')
        health,health_ms=command(args.syune,'health','--state-root',state,'--json')
        status,status_ms=command(args.syune,'status','--state-root',state,'--json')
        shown,_=command(args.syune,'config','show','--state-root',state,'--json')
        valid,_=command(args.syune,'config','validate','--state-root',state,'--json')
        upgrade,_=command(args.syune,'upgrade','check','--state-root',state,'--json')
        tools,mcp_health,studied,recall,mcp_ms,recall_ms=asyncio.run(mcp_check(args.syune,state,library,source))
        a,b=json.loads(first),json.loads(second)
        assert version=='0.1.0' and a['instance_id']==b['instance_id'] and b['created'] is False
        assert json.loads(health)['overall']=='HEALTHY' and json.loads(valid)['valid']
        assert json.loads(upgrade)['migration_required'] is False
        assert mcp_health['retrieval_index']=='available' and studied['is_studied'] and recall['candidates']
        expected={'syune_health','syune_status','syune_capabilities','syune_source_status','syune_memory_get',
                  'syune_recall','syune_cognize','syune_council','syune_plan','syune_study_source'}
        assert tools==expected
        result={'status':'PASS','version':version,'instance_id_stable':True,'health':json.loads(health),
            'status_result':json.loads(status),'config':json.loads(shown),'upgrade':json.loads(upgrade),
            'mcp_tools':sorted(tools),'mcp_health':mcp_health,'timings_ms':{'version_process':version_ms,
            'init_process':init_ms,'repeat_init_process':reinit_ms,'health_process':health_ms,
            'status_process':status_ms,'mcp_startup_connect_health':mcp_ms,'first_recall':recall_ms}}
        args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps({'status':'PASS','output':str(args.output)}))


if __name__=='__main__':main()
