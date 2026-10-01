import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def imports(path):
    tree=ast.parse(path.read_text(encoding="utf-8"));out=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):out.extend(x.name for x in node.names)
        elif isinstance(node,ast.ImportFrom):out.append(node.module or "")
    return out
def test_council_is_read_only_nonagent_provider_free():
    forbidden=("openai","anthropic","requests","httpx","socket","subprocess","syune.study","syune.learning","syune.gateway","syune.executive","syune.providers")
    for path in (ROOT/"src/syune/council").glob("*.py"):
        assert all(not name.startswith(forbidden) for name in imports(path)),path
        text=path.read_text(encoding="utf-8").casefold()
        assert all(term not in text for term in ("put_many","add_association","learningsignal","dispatch_agent","control_core","majority_vote","execute_action")),path
    gateway=(ROOT/"src/syune/gateway/mcp/server.py").read_text(encoding="utf-8").casefold()
    assert 'name="syune_council"' in gateway and "majority_vote" not in gateway
