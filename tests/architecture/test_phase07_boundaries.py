"""Phase 07 learning is explicit, local, non-MCP, and separate from canonical memory."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): result.append(node.module or "")
    return result


def test_learning_boundaries_and_no_mcp_mutation_tools():
    forbidden = ("openai", "anthropic", "langchain", "chromadb", "faiss", "qdrant", "neo4j",
                 "pinecone", "requests", "httpx", "socket", "subprocess", "syune.executive",
                 "syune.council", "syune.domains", "syune.gateway")
    for path in (ROOT / "src/syune/learning").glob("*.py"):
        assert all(not name.startswith(forbidden) for name in imports(path)), path
        text = path.read_text(encoding="utf-8").casefold()
        assert "dispatch_agent" not in text and "background daemon" not in text
    for path in (ROOT / "src/syune/memory").glob("*.py"):
        assert all(not name.startswith("syune.learning") for name in imports(path)), path
    for path in (ROOT / "src/syune/retrieval").glob("*.py"):
        assert all(not name.startswith("syune.learning") for name in imports(path)), path
    gateway = (ROOT / "src/syune/gateway/mcp/server.py").read_text(encoding="utf-8")
    assert "learning" not in gateway.casefold()
