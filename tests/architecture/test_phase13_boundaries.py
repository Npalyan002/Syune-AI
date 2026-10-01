import ast
from pathlib import Path
ROOT=Path(__file__).parents[2];PACKAGE=ROOT/"src/syune/executive"
def test_runtime_has_no_generic_shell_network_agent_control_or_learning_commit():
    forbidden={"subprocess","socket","requests","httpx","aiohttp","urllib","mcp","openai","anthropic","syune.learning","syune.gateway"}
    for path in PACKAGE.glob("*.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"));source=path.read_text(encoding="utf-8").casefold()
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or ""]
                assert not any(any(name==bad or name.startswith(bad+".") for bad in forbidden) for name in names)
        assert "shell_exec" not in source and "python_eval" not in source and "arbitrary_http" not in source
        assert "dispatch_agent(" not in source and "control_core(" not in source and "learningsignal(" not in source
def test_no_background_executor_or_production_adapter():
    names={p.name for p in PACKAGE.glob("*.py")};assert "daemon.py" not in names and "production.py" not in names
