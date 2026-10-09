# Installation

SYUNE 2.0.0 is validated with CPython 3.12 on Windows, Linux, and macOS. Package
metadata permits `>=3.12,<4`; other Python versions remain compatibility targets.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install syune==2.0.0
.\.venv\Scripts\syune.exe --version
```

PEP 440 and the human release/tag form both use `2.0.0`. Runtime
dependencies are MCP 2.x and pypdf 6.x. Provider credentials are not needed for memory.
