"""Fail closed on state, secret, cache, or machine-path leakage in build artifacts."""
import argparse,json,tarfile,zipfile
from pathlib import Path


def members(path):
    if path.suffix=='.whl':
        with zipfile.ZipFile(path) as archive:return [(x.filename,archive.read(x)) for x in archive.infolist() if not x.is_dir()]
    with tarfile.open(path) as archive:return [(x.name,archive.extractfile(x).read()) for x in archive.getmembers() if x.isfile()]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dist',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    artifacts=[]
    for path in sorted(args.dist.iterdir()):
        if path.suffix not in ('.whl','.gz'):continue
        files=members(path);names=[name.lower().replace('\\','/') for name,_ in files]
        forbidden=[name for name in names if '/.git/' in '/'+name or '/.syune/' in '/'+name or name.endswith(('.db','.sqlite','.sqlite3','.pyc','.log','.env')) or '/__pycache__/' in '/'+name]
        wheel_path_hits=[]
        if path.suffix=='.whl':
            for name,data in files:
                if b'E:\\AI\\SYUNE' in data or b'E:/AI/SYUNE' in data:wheel_path_hits.append(name)
            assert any(name.endswith('.dist-info/entry_points.txt') for name in names)
            assert any(name.endswith('syune/cli/app.py') for name in names)
        assert not forbidden and not wheel_path_hits,(forbidden,wheel_path_hits)
        artifacts.append({'name':path.name,'bytes':path.stat().st_size,'files':len(files),'forbidden_files':forbidden,'machine_path_hits':wheel_path_hits})
    assert {Path(x['name']).suffix for x in artifacts}=={'.whl','.gz'}
    result={'status':'PASS','artifacts':artifacts,'license':'LICENSE_DECISION_REQUIRED'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
