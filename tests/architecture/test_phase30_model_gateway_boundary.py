import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P0=("learning","cognition","council","executive")

def test_p0_modules_cannot_import_provider_transports_or_sdks():
    forbidden={"openai","anthropic","google.generativeai","urllib.request","requests","httpx"}
    for area in P0:
        for path in (ROOT/"src/syune"/area).rglob("*.py"):
            tree=ast.parse(path.read_text(encoding="utf-8-sig"))
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(alias.name for alias in node.names)
                elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            assert not any(name in forbidden or any(name.startswith(x+".") for x in forbidden) for name in imports),(path,imports)

def test_transaction_boundary_has_distinct_identity_types():
    from syune.model_gateway import CognitiveTransactionResult, ModelExecutionResult
    assert CognitiveTransactionResult is not ModelExecutionResult
