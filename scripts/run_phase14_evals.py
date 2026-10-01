"""Explicit local eval CLI: quick, full, security, resilience, e2e, performance, soak."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from syune.evals.model import *
from syune.evals.runner import run_suite
from syune.evals.reporting import report, to_json

ROOT=Path(__file__).resolve().parents[1]
GROUPS={
    'ARCHITECTURE':('architecture',), 'MEMORY':('memory','repository','corruption'),
    'STUDY':('study','multimodal'), 'RETRIEVAL':('retrieval',),
    'LEARNING':('learning',), 'COGNITION':('cognitive',), 'PROFILES':('profile',),
    'MULTIMODAL':('multimodal','perception'), 'COUNCIL':('council',),
    'PLANNING':('executive_contracts','test_executive.'), 'EXECUTION':('execution','approval'),
    'RESILIENCE':('resilience','restart'), 'SECURITY':('boundaries','resource_security'),
    'REGRESSION':('eval_contract','test_regression'),
}
INVARIANTS={
    'ARCHITECTURE':'dependency and authority boundaries remain intact',
    'MEMORY':'canonical identities, references and decoded records remain valid',
    'STUDY':'explicit bounded ingestion is idempotent and source preserving',
    'RETRIEVAL':'curated relevant entities recalled without canonical mutation',
    'LEARNING':'explicit bounded overlay updates preserve canonical confidence',
    'COGNITION':'structural inference uses existing evidence and preserves gaps',
    'PROFILES':'profile differences preserve shared facts and provenance',
    'MULTIMODAL':'shared memory retains exact modality provenance and failure isolation',
    'COUNCIL':'agreement never grants truth authority; disagreement and minority survive',
    'PLANNING':'explicit goals yield bounded reviewable plans and visible blockers',
    'EXECUTION':'exact external approval gates side effects and idempotency',
    'RESILIENCE':'crash recovery reconciles without blind retry; corruption is explicit',
    'SECURITY':'no generic execution, unauthorized target or unbounded local artifact',
    'REGRESSION':'missing metrics and incomplete coverage fail closed',
}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['quick','full','security','resilience','e2e','performance','soak']);args=parser.parse_args()
    out=ROOT/'.syune/phase14';out.mkdir(parents=True,exist_ok=True)
    if args.mode in ('performance','soak'):
        mode='scale' if args.mode=='performance' else 'soak'
        return subprocess.call([sys.executable,str(ROOT/'scripts/benchmark_phase14.py'),mode,'--output',str(ROOT/('.syune/phase14-'+mode+'.json'))],cwd=ROOT)
    targets={'full':['tests'],'quick':['tests/unit','tests/phase14'],'security':['tests/architecture','tests/phase14/test_resource_security.py'],
        'resilience':['tests/phase14/test_resilience.py','tests/phase14/test_restart_approval.py'],'e2e':['tests/phase14/test_e2e.py']}[args.mode]
    xml=out/(args.mode+'.xml')
    completed=subprocess.run([sys.executable,'-m','pytest',*targets,'-q','--junitxml='+str(xml)],cwd=ROOT)
    if not xml.exists(): return completed.returncode or 1
    nodes=ET.parse(xml).findall('.//testcase');cases=[];checks={}
    for category,patterns in GROUPS.items():
        selected=[n for n in nodes if any(p in n.get('classname','')+'.'+n.get('name','') for p in patterns)]
        if not selected and args.mode!='full':continue
        case=EvalCase(category.lower(),Category(category),INVARIANTS[category],'deterministic pytest fixtures; isolated stores and explicit test-host approval',
            (EvalExpectation(INVARIANTS[category],'failures',0,0),EvalExpectation('at least one case ran without skip','executed',1,100000)),
            tuple(n.get('classname','')+'.'+n.get('name','') for n in selected) or ('missing-tests',))
        cases.append(case)
        def check(selected=selected):
            failures=sum(n.find('failure') is not None or n.find('error') is not None or n.find('skipped') is not None for n in selected)
            executed=len(selected)-failures
            return (EvalMetric('failures',failures),EvalMetric('executed',executed)),tuple(n.get('classname','')+'.'+n.get('name','') for n in selected)
        checks[case.id]=check
    if args.mode=='full':
        case=EvalCase('performance',Category.PERFORMANCE,'bounded scale and full-stack soak completed',
            'synthetic SQLite memory and local sandbox pipeline',
            (EvalExpectation('large memory completed','largest_entities',10000,100000),
             EvalExpectation('bounded soak completed','soak_seconds',600,1900),
             EvalExpectation('no soak errors','errors',0,0)),
            ('phase14-scale.json','phase14-soak.json'))
        cases.append(case)
        def performance_check():
            scale=json.loads((ROOT/'.syune/phase14-scale.json').read_text())
            soak=json.loads((ROOT/'.syune/phase14-soak.json').read_text())
            if scale['status']!='PASS' or soak['status']!='PASS':raise ValueError('performance incomplete')
            return (EvalMetric('largest_entities',max(x['entities'] for x in scale['results'])),EvalMetric('soak_seconds',soak['duration_seconds']),EvalMetric('errors',len(soak['errors']))),case.evidence
        checks['performance']=performance_check
    suite=EvalSuite('phase14-'+args.mode,tuple(cases));run=run_suite(suite,checks,'phase14-validation')
    result=report(run,required_cases=tuple(c.id for c in cases),limitations=('separate scale/soak/architecture/diff/commit gates required',))
    (out/(args.mode+'.json')).write_text(to_json(result),encoding='utf-8')
    (out/(args.mode+'-cases.json')).write_text(json.dumps([{'id':c.id,'description':c.description,'fixture':c.fixture,'evidence':c.evidence} for c in cases],indent=2))
    print('Eval readiness:',result.readiness.value,'test count:',len(nodes))
    return completed.returncode or int(bool(run.failures))

if __name__=='__main__':raise SystemExit(main())
