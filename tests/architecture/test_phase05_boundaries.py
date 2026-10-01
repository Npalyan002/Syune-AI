"""Gateway exposes only the Phase 16 approved public MCP capabilities."""
import ast
from pathlib import Path

from syune.gateway.mcp.server import TOOL_ALLOWLIST
from syune.gateway.mcp.lean import LEAN_TOOL_ALLOWLIST

ROOT = Path(__file__).resolve().parents[2] / "src" / "syune" / "gateway" / "mcp"
EXPECTED = {"syune_health", "syune_status", "syune_capabilities", "syune_source_status",
            "syune_memory_get", "syune_recall", "syune_cognize", "syune_council",
            "syune_plan", "syune_study_source"}


def test_explicit_allowlist_and_no_execution_or_network_imports():
    assert TOOL_ALLOWLIST == EXPECTED
    decorators = set()
    for path in ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                names = []
            assert all(not name.startswith(("subprocess", "socket", "urllib", "requests", "httpx",
                                             "openai", "anthropic", "syune.providers"))
                       for name in names), path
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "tool":
                        decorators.update(keyword.value.value for keyword in decorator.keywords
                                          if keyword.arg == "name" and isinstance(keyword.value, ast.Constant))
    assert decorators == EXPECTED | LEAN_TOOL_ALLOWLIST
