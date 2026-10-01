import ast
from pathlib import Path

import syune
from syune import Syune

ROOT=Path(__file__).resolve().parents[2]


def test_public_exports_and_generic_host_are_detached():
    forbidden=("SQLite","Repository","Store","Adapter","SupervisedExecutiveService")
    assert all(not any(term in name for term in forbidden) for name in syune.__all__)
    assert not hasattr(Syune,"execute") and not hasattr(Syune,"execute_approved")
    tree=ast.parse((ROOT/"examples/host_integration/host.py").read_text(encoding="utf-8"))
    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom): imports.append(node.module or "")
        elif isinstance(node,ast.Import): imports.extend(alias.name for alias in node.names)
    assert imports==["pathlib","argparse","syune"]
    assert all(not name.startswith(("syune.memory","syune.product","syune.executive","sqlite3")) for name in imports)


def test_public_runtime_has_no_network_shell_or_rest_surface():
    text="\n".join(path.read_text(encoding="utf-8") for folder in ("api","sdk")
                   for path in (ROOT/f"src/syune/{folder}").glob("*.py")).casefold()
    assert all(term not in text for term in ("subprocess","os.system","fastapi","flask","requests.","httpx.","socket."))
    assert "art-dep-ai" not in text
