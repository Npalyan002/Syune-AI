import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def imports(path):
    tree=ast.parse(path.read_text(encoding="utf-8"));out=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):out.extend(x.name for x in node.names)
        elif isinstance(node,ast.ImportFrom):out.append(node.module or "")
    return out
def test_perception_has_no_network_execution_epistemic_or_modality_storage():
    forbidden=("requests","httpx","aiohttp","urllib","socket","subprocess","openai","anthropic","syune.learning","syune.cognition")
    for path in (ROOT/"src/syune/perception").glob("*.py"):
        assert all(not name.startswith(forbidden) for name in imports(path)),path
        text=path.read_text(encoding="utf-8").casefold()
        assert all(term not in text for term in ("face_recognition","biometric","speaker_identity","claim(","memoryrepository","sqlite3")),path
    assert not any((ROOT/"src/syune").rglob("*image*.sqlite*"))
    assert not any((ROOT/"src/syune").rglob("*audio*.sqlite*"))
    assert not any((ROOT/"src/syune").rglob("*video*.sqlite*"))
