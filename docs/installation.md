# Installation

SYUNE 2.0.0 is validated with CPython 3.12 on Windows, Linux, and macOS. Package
metadata permits `>=3.12,<4`; other Python versions remain compatibility targets. These
instructions install the immutable GitHub release source and do not assume that 2.0.0
has been published to PyPI.

```powershell
git clone https://github.com/Npalyan002/Syune-AI.git
Set-Location Syune-AI
git checkout v2.0.0
if ((git rev-parse HEAD) -ne '23d76717feff156849acc5e6b66aac088cd92afb') { throw 'unexpected release commit' }
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\syune.exe --version
```

POSIX shells use `.venv/bin/python` and `.venv/bin/syune`. A locally built wheel from
the same commit may be installed instead. Verify `syune --version` reports `2.0.0`.

PEP 440 and the human release/tag form both use `2.0.0`. Runtime
dependencies are MCP 2.x and pypdf 6.x. Provider credentials are not needed for memory.
