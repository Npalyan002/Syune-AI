# Product refactor summary

SYUNE now defaults to governed memory, authorized retrieval, bounded context assembly, and reliable model access. The full cognitive architecture is preserved at tag `syune-full-cognitive-pre-lean`; it is not the default product.

Default startup opens memory and study stores, builds the local retrieval index, and creates context assembly. Learning, profiles, council, planner, and execution are absent. Legacy SDK research calls remain lazy and emit `DeprecationWarning`.

Decision: **LEAN_CORE_READY**. This means the lean core is technically coherent and regression-safe; it does not claim market demand or independent benchmark superiority.
