# RC1 source-tree audit

Audit date: 2026-09-30. Candidate: `1.0.0-rc1`.

Every pre-release working-tree item was classified before staging:

- **RELEASE_SOURCE:** Lean runtime, public SDK/API/MCP, configuration/state, audit,
  context and ModelGateway source; version and packaging metadata; tests; public docs;
  security, migration, backup, dependency and release records; examples; validation
  scripts and feature-freeze marker.
- **VALIDATION_EVIDENCE:** `docs/product_refactor`, `docs/lean_v1_validation`,
  `docs/lean_v1_blocker_closure`, the public historical-evaluation summary, and Lean
  benchmark gates. Raw databases, provider call ledgers, repeated manifests and generated
  phase outputs were removed from the post-v1 public branch; tagged history preserves them.
- **LOCAL_ONLY / TEMPORARY:** `.test-tmp`, `phase24-full-tmp`, and pytest/tmp
  workspaces below `docs/evals/phase19`, `phase20`, and `phase21`. They are excluded by
  precise ignore rules and are not staged, packaged, or deleted.

No unclassified status item remains. Build outputs, virtual environments, caches,
runtime databases, local configuration, credentials, editor files, and logs are excluded
by `.gitignore`. Release staging uses explicit paths rather than a blanket add.

The release scan found no embedded developer checkout path in primary release surfaces
or package files and no recognized live credential/token pattern. Archive inspection is
repeated for the final wheel and sdist. Historical tags and final `v1.0.0` are out of
scope and remain untouched.
