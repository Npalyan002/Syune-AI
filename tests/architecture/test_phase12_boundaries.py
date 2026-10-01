import ast
from pathlib import Path
ROOT=Path(__file__).parents[2];PACKAGE=ROOT/"src"/"syune"/"executive"
def test_executive_has_no_execution_or_side_effect_dependencies():
    forbidden={"subprocess","socket","requests","httpx","aiohttp","urllib","mcp","openai","anthropic","syune.learning","syune.study","syune.gateway"}
    for path in PACKAGE.glob("*.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"));source=path.read_text(encoding="utf-8").casefold()
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or ""]
                assert not any(any(name==bad or name.startswith(bad+".") for bad in forbidden) for name in names)
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                assert node.name not in {"execute","run_action","dispatch","call_tool","call_agent","approve","authorize"}
        assert "learningsignal(" not in source and "control_core(" not in source and "os.system" not in source
def test_gateway_has_no_executive_surface():
    source=(ROOT/"src/syune/gateway/mcp/server.py").read_text(encoding="utf-8").casefold()
    assert 'name="syune_plan"' in source
    assert all(term not in source for term in ('name="syune_execute', "execute_approved", "plan_and_execute"))
