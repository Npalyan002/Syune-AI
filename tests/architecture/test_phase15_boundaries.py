import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def test_product_has_no_legacy_network_telemetry_or_destructive_reset():
    for path in (ROOT/'src/syune/product').glob('*.py'):
        text=path.read_text(encoding='utf-8-sig');tree=ast.parse(text)
        assert 'ART-DEP-AI' not in text and 'E:\\AI\\SYUNE' not in text
        assert 'rmtree' not in text and 'unlink(' not in text
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or '']
                assert all(x not in {'requests','httpx','socket','urllib'} for x in names)
    assert 'telemetry: bool = False' in (ROOT/'src/syune/product/config.py').read_text()


def test_single_console_entry_point_and_canonical_version():
    pyproject=(ROOT/'pyproject.toml').read_text()
    assert 'version = "1.0.2"' in pyproject and 'syune = "syune.cli.app:main"' in pyproject
    assert '1.0.2' not in (ROOT/'src/syune/__init__.py').read_text()
