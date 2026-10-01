import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def imports(path):
    tree=ast.parse(path.read_text(encoding="utf-8"));out=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):out.extend(x.name for x in node.names)
        elif isinstance(node,ast.ImportFrom):out.append(node.module or "")
    return out

def test_profiles_are_static_shared_read_only_policy():
    path=ROOT/"src/syune/cognition/profiles.py";names=imports(path)
    forbidden=("sqlite3","syune.memory","syune.learning","syune.study","syune.gateway","syune.executive","syune.council","openai","anthropic","requests","subprocess")
    assert all(not name.startswith(forbidden) for name in names)
    text=path.read_text(encoding="utf-8").casefold()
    assert all(term not in text for term in ("memoryrepository","learningledger","plasticityoverlay","auto_classifier","profile_router","dispatch_agent","control_core"))
    assert not list((ROOT/"src/syune/domains").glob("*.py"))
