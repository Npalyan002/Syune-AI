import ast
from pathlib import Path

from syune.core import ObservationId
from syune.memory import InMemoryReferenceRepository, MemoryTrace, Observation


def test_observation_is_memory_owned_not_study_owned():
    root = Path(__file__).resolve().parents[2]
    for path in (root / "src" / "syune" / "memory").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [
            node.module for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        imports += [
            alias.name for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        assert all(not name.startswith("syune.study") for name in imports)


def test_public_observation_contract():
    assert ObservationId.__name__ == "ObservationId"
    assert Observation.__name__ == "Observation"
    assert hasattr(InMemoryReferenceRepository, "put")
    assert "entity_id" in MemoryTrace.__dataclass_fields__
