"""Audit-only artifact and baseline integrity verification; no production writes."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[2]
audit = root / 'docs/phase17'
required = [
    'PHASE_17_AUDIT.md', 'SYUNE_CURRENT_ARCHITECTURE.md', 'SYUNE_CAPABILITY_MATRIX.md',
    'SYUNE_GAP_REGISTER.md', 'SYUNE_COMPETITIVE_GAP.md', 'SYUNE_TECHNICAL_DEBT.md',
    'SYUNE_RUNTIME_COST_MAP.md', 'SYUNE_TARGET_ARCHITECTURE_V2.md', 'PHASE_17_VALIDATION.md'
]
baseline = json.loads((audit / 'evidence/repository-inventory.json').read_text(encoding='utf-8-sig'))
changed = []
for row in baseline['tracked_files']:
    path = root / row['path']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
        changed.append(row['path'])
missing = [name for name in required if not (audit / name).is_file()]
broken = []
whitespace = []
for name in required:
    path = audit / name
    if not path.exists(): continue
    content = path.read_text(encoding='utf-8-sig')
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if target != 'evidence/artifact-check.json' and '://' not in target and not (audit / target.split('#')[0]).exists():
            broken.append([name, target])
    for line, text in enumerate(content.splitlines(), 1):
        if text != text.rstrip():
            whitespace.append([name, line])
def rows(name):
    text = (audit / name).read_text(encoding='utf-8-sig')
    return [[x.strip() for x in line.strip('|').split('|')] for line in text.splitlines() if line.startswith('| ') and not line.startswith('| ---')]
matrix = rows('SYUNE_CAPABILITY_MATRIX.md')[1:]
gaps = rows('SYUNE_GAP_REGISTER.md')[1:]
dispositions = {'KEEP_CORE','KEEP','MODIFY','EXTEND','OPTIONAL','RESEARCH','DEPRECATE','REPLACE','MISSING','UNKNOWN'}
matrix_errors = [r for r in matrix if len(r) != 10 or r[6] not in dispositions]
gap_errors = [r for r in gaps if len(r) != 10 or r[6] not in dispositions]
diff = subprocess.run(['git','diff','--check'], cwd=root, capture_output=True, text=True)
untracked = subprocess.check_output(['git','ls-files','--others','--exclude-standard'], cwd=root, text=True).splitlines()
outside = [p for p in untracked if not p.startswith('docs/phase17/')]
report = {
    'baseline_commit': baseline['commit'],
    'baseline_files_checked': len(baseline['tracked_files']),
    'changed_baseline_files': changed, 'missing_reports': missing,
    'broken_local_links': broken, 'trailing_whitespace': whitespace,
    'capability_rows': len(matrix), 'gap_rows': len(gaps),
    'matrix_errors': matrix_errors, 'gap_errors': gap_errors,
    'new_files_outside_audit': outside, 'git_diff_check_exit': diff.returncode,
    'git_diff_check_output': diff.stdout + diff.stderr,
}
report['status'] = 'PASS' if not any([changed, missing, broken, whitespace, matrix_errors, gap_errors, outside, diff.returncode]) else 'FAIL'
(audit / 'evidence/artifact-check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(report['status'] != 'PASS')

