# Compatibility matrix

| SYUNE package | Public API | State schema | MCP contract | Python | Tested OS |
| --- | --- | ---: | --- | --- | --- |
| 0.1.0 | 1 | 1 | 1 | >=3.12,<4 | Windows 11 / CPython 3.12.10 |

Public API and MCP versions negotiate independently of package version. State schema compatibility is checked before runtime open and is never migrated automatically. Python and OS entries outside the tested row are declared support ranges, not validation claims.

Compatibility rules: additive optional public fields are backward compatible; required-field removal/rename, semantic meaning changes, and enum changes without fallback are breaking. Internal storage changes are compatible when observable v1 semantics remain stable. During pre-1.0, deprecations receive a changelog entry and migration note before removal. Phase 18 owns the final v1.0 guarantee.
