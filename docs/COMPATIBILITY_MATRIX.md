# Compatibility matrix

| SYUNE package | Public API | State schema | MCP contract | Python | Tested OS |
| --- | --- | ---: | --- | --- | --- |
| 0.1.0 | 1 | 1 | 1 | >=3.12,<4 | Windows 11 / CPython 3.12.10 |
| 1.0.x–1.1.0 | 1 | 1 | 1 | >=3.12,<4 | Windows, macOS, Ubuntu CI |
| 2.0.0 | 1 | 1 | 1 | >=3.12,<4 | Windows, macOS, Ubuntu CI; Ubuntu container validation |

Public API and MCP versions negotiate independently of package version. State schema compatibility is checked before runtime open and is never migrated automatically. Python and OS entries outside the tested row are declared support ranges, not validation claims.

Compatibility rules: additive optional public fields are backward compatible; required-field removal/rename, semantic meaning changes, and enum changes without fallback are breaking. Internal storage changes are compatible when observable public API v1 semantics remain stable. The package major version, public API version, state schema, and MCP contract are intentionally versioned independently.
