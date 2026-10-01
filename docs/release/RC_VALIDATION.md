# RC1 validation record

Candidate: `1.0.0-rc1` (PEP 440 artifact version `1.0.0rc1`).

Validation date: 2026-09-30. Platform: Windows (`win32`), CPython 3.12.14.

- Wheel and sdist build: pass; independent builds were byte-for-byte identical.
- Artifact content and sanitized secret scan: pass; known secret leaks 0.
- Clean wheel and sdist dependency installs: pass; no editable install or PYTHONPATH.
- Exact packaged quickstart: pass.
- Installed-package SDK, Lean MCP, five detachability modes, default research isolation,
  structured synthetic ModelGateway, budget, identity, audit and restart: pass.
- Latest pre-RC Lean state reopen: pass without migration; memory/audit retained.
- Offline backup/destroy/restore and corruption/missing-store failures: pass.
- Focused license/product/interface regression: 22 passed, 1 expected deprecation warning.
- Complete repository regression: 380 passed, 0 failed, 0 skipped, 2 expected
  deprecation warnings.
- Apache-2.0: canonical `LICENSE`, SPDX project metadata, wheel
  `License-Expression`/`License-File`, and wheel/sdist license payload all pass.
- `NOTICE_NOT_REQUIRED`: SYUNE does not bundle or derive from material carrying an
  upstream NOTICE file; dependencies are resolved separately rather than vendored.
- Independent pre-commit wheel and sdist builds were byte-for-byte reproducible. Final
  post-commit hashes are recorded outside the self-containing sdist in the release report.
- Live paid provider rerun: not performed; prior Phase 29 evidence retained.
- Linux: not available in this validation environment and not claimed as RC-tested.

RC preparation is **READY** for the authorized `v1.0.0-rc1` commit and annotated tag.
No copyright attribution was invented because no legal holder was established; that is
not required to apply Apache-2.0. Final `v1.0.0` remains out of scope pending RC review
and separate authorization.
