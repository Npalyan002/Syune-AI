"""Static Phase 03 boundaries; no cognitive or external runtime is authorized."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "src" / "syune" / "study"
FORBIDDEN_IMPORTS = (
    "syune.retrieval", "syune.cognition", "syune.domains", "syune.council",
    "syune.executive", "syune.gateway", "syune.providers",
    "openai", "anthropic", "langchain", "requests", "httpx", "aiohttp",
    "urllib", "socket", "subprocess", "mcp",
)


def test_study_import_direction_and_no_network_provider_dependency():
    for path in STUDY.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for name in imports:
            assert not name.startswith(FORBIDDEN_IMPORTS), (path, name)


def test_documents_are_never_executed_or_mutated():
    for path in STUDY.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in {"eval", "exec", "compile"}
                elif isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in {
                        "write_bytes", "write_text", "unlink", "rename",
                        "rmtree", "system", "popen",
                    }


def test_memory_remains_independent_of_study():
    for path in (ROOT / "src" / "syune" / "memory").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("syune.study")
            elif isinstance(node, ast.Import):
                assert all(not alias.name.startswith("syune.study") for alias in node.names)
