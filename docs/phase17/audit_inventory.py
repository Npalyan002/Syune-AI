"""Audit-only tracked-file inventory, symbols, and baseline integrity evidence."""
import ast, hashlib, json, subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[2]
rows = []
for name in subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines():
    path = root / name
    if not path.is_file():
        continue
    data = path.read_bytes()
    row = {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if path.suffix == '.py':
        tree = ast.parse(data.decode('utf-8-sig'))
        row['symbols'] = [{'name': n.name, 'line': n.lineno} for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
    rows.append(row)
output = {'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(), 'tracked_files': rows}
(root / 'docs/phase17/evidence/repository-inventory.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps({'tracked_files': len(rows), 'python_files': sum('symbols' in r for r in rows), 'source_files': sum(r['path'].startswith('src/') for r in rows)}))
