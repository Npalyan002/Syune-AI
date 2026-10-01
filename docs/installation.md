# Installation

RC1 is validated on Windows 11 with CPython 3.12. Metadata permits `>=3.12,<4`;
other platforms/versions are compatibility targets, not RC1 validated claims.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install syune==1.0.0
.\.venv\Scripts\syune.exe --version
```

PEP 440 and the human release/tag form both use `1.0.0`. Runtime
dependencies are MCP 2.x and pypdf 6.x. Provider credentials are not needed for memory.
