import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def test_full_runtime_no_generic_execution_or_eval_to_runtime_dependency():
    forbidden={'eval','exec','compile'}
    for path in (ROOT/'src/syune').rglob('*.py'):
        text=path.read_text(encoding='utf-8-sig');tree=ast.parse(text)
        assert 'ART-DEP-AI' not in text
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                assert node.func.id not in forbidden,(path,node.func.id)
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module or '']
                assert all(n not in {'subprocess','requests','httpx','socket'} for n in names),(path,names)
                if 'evals' not in path.parts: assert all(not n.startswith('syune.evals') for n in names)
    approval=(ROOT/'src/syune/executive/approval_runtime.py').read_text()
    assert 'ApprovalToken(' not in approval
