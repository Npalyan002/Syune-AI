# RC1 dependency and license audit

Runtime direct dependencies are `mcp>=2,<3` (MIT) and `pypdf>=6,<7`
(BSD-3-Clause). Hatchling is build-only and pytest is development-only. Provider
credentials/packages are not required for memory or context modes. Research modules add
no declared runtime dependency.

The clean Windows install resolved transitive licenses as MIT/MIT-0, BSD-3-Clause,
Apache-2.0, PSF/PSF-2.0, or `Apache-2.0 OR BSD-3-Clause`; no unknown or declared copyleft
license was observed in installed metadata. SYUNE itself is licensed under Apache-2.0.
This is an inventory, not a legal conclusion. The project does not bundle dependency
source or an upstream NOTICE file, so no dependency NOTICE content is reproduced.
