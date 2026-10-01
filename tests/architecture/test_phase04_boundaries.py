"""Phase 04 keeps recall read-only and provider/network free."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "syune" / "retrieval"
FORBIDDEN = ("openai", "anthropic", "requests", "httpx", "aiohttp", "socket", "urllib",
             "subprocess", "syune.gateway", "syune.providers", "syune.executive",
             "syune.domains", "syune.council", "syune.cognition")


def test_retrieval_has_no_external_or_mutating_dependency():
    for path in ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                names = []
            assert all(not name.startswith(FORBIDDEN) for name in names), path
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"put", "put_many", "add_association", "write_bytes",
                                              "write_text", "unlink", "execute", "executemany"}, path
