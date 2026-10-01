import ast
from pathlib import Path

import syune

ROOT = Path(__file__).resolve().parents[2]
MEMORY_ROOT = ROOT / "src" / "syune" / "memory"
FORBIDDEN = {
    "syune.study", "syune.retrieval", "syune.cognition", "syune.domains",
    "syune.council", "syune.executive", "syune.gateway", "syune.providers",
    "syune.storage", "ART-DEP-AI",
}


def test_package_import_and_language_boundary():
    assert syune.__name__ == "syune"
    assert (ROOT / "pyproject.toml").exists()
    assert not list((ROOT / "src").rglob("*.rs"))
    assert not list((ROOT / "src").rglob("*.ts"))


def test_memory_imports_only_core_and_memory():
    for path in MEMORY_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert not any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN), (path, name)


def test_no_runtime_in_future_modules():
    for name in ("domains", "gateway", "providers", "storage"):
        assert not list((ROOT / "src" / "syune" / name).glob("*.py"))
