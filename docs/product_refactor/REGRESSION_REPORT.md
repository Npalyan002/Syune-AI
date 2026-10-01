# Regression report

Required gates are the complete pre-refactor suite (baseline 371 tests), lean isolation tests, no-LLM remember/recall/context/forget flow, authorization-context isolation, Phase 29/30 ModelGateway suites, and an optional real-provider test only when credentials are explicitly supplied.

Final command: `.venv\\Scripts\\python.exe -m pytest -q --basetemp=lean-full-test-tmp -p no:cacheprovider`.

Result: **375 passed, 2 warnings in 966.92s**. This is the 371-test baseline plus four lean tests. Both warnings are intentional `DeprecationWarning` emissions proving lazy research compatibility calls are visible to migrators. No test was skipped and the process exited 0.
