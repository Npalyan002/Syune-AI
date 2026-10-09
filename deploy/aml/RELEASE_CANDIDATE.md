# Proposed release candidate: 1.1.1-aml.1

This is a local proposal only. No commit, tag, image, release, or deployment has
been created. It is based on historical commit
`fb76ca390d0774a95a522517d129730c3446a312` (`v1.1.0`) plus the uncommitted
Phase 02A through 04B-2 working-tree changes. It must not be described as the
historical `v1.1.0` artifact.

## Reproducibility evidence

- Python 3.12.10 and uv 0.12.24.
- `uv sync --check` resolves 43 packages and confirms 42 installed packages
  without changing `uv.lock`.
- `uv.lock` SHA-256:
  `93dceadc5cb5da8cc19ae93b4c24fd8040787410146bcdc5b05d22ed07c17324`.
- `pyproject.toml` SHA-256:
  `cdf087571d1888813a6f7e37996251e6d3b58b3750b41094ed7b53b963141844`.
- Python OCI index: `sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db`;
  Linux amd64 child: `sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4`.
- Nginx OCI index: `sha256:30f1c0d78e0ad60901648be663a710bdadf19e4c10ac6782c235200619158284`;
  Linux amd64 child: `sha256:09ab424a8c788f8d0fe3a64429f6d19dfa526885c8609b748d0943a75dcb9f8c`.
- Both OCI index bodies were fetched from `registry-1.docker.io`, hashed locally,
  and matched the registry `Docker-Content-Digest` on 2026-10-09.
- Nginx 1.28.0 `nginx -t` succeeded with synthetic local TLS files and only
  environment-specific mount, upstream, log, and PID paths substituted.
- `source-change-manifest.sha256` records every tracked modification and
  non-ignored untracked source/deployment/test file relative to the baseline.

## Promotion gate

Promotion requires an approved immutable source commit and successful manual
execution of `.github/workflows/aml-container-validation.yml` at that exact
revision. The workflow prepares the Docker build, Compose validation, image
inspection, container Add/Search and restart tests, log/image secret checks,
and full regression suite. It has not been remotely executed, so all cloud
container results remain pending. Production-equivalent capacity evidence and
separate deployment authorization are also required.
