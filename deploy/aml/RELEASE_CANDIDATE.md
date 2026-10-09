# SYUNE 2.0.0 release candidate record

SYUNE 2.0.0 is the next major-release candidate built from historical baseline
`fb76ca390d0774a95a522517d129730c3446a312` (`v1.1.0`) plus the validated Phase
02A through 04B integration, security, reliability, and deployment work. The
historical tag remains unchanged. Until an authorized `v2.0.0` tag and release
exist, identify this candidate by its exact Git commit rather than by `v1.1.0`.

The pre-finalization source baseline
`3748400609edb8aec181b40df7a19f69c1379c6f` passed GitHub Actions run
`37911437399` across Windows, macOS, Ubuntu, and the complete Ubuntu container
stack. The version/documentation finalization commit must pass the same manual
workflow before release authorization.

## Reproducibility evidence

- Python 3.12.10 and uv 0.12.24.
- `uv sync --frozen --check` confirms 42 installed packages
  without changing `uv.lock`.
- `uv.lock` SHA-256:
  `e9d4b0db6980a7cc1f4b1d0ed4ca834e05c144e8bbc13bb1acb6e77e026a5b30`.
- `pyproject.toml` SHA-256:
  `8b19980152eb44011183aab49b44470b797cac8a4f92d2759639f9b22bfdb836`.
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
  Text hashes use canonical LF line endings so Windows and Linux checkouts
  reproduce the same values.

## Promotion gate

Promotion requires the immutable 2.0.0 candidate commit and a successful manual
execution of `.github/workflows/aml-container-validation.yml` at that exact
revision. Review Docker build, Compose validation, image inspection, Add/Search,
100-candidate retrieval, restart recovery, log/image secret checks, cleanup,
and the full regression suite. A successful candidate run is necessary but does
not authorize a tag, release, package publication, AML submission, or public
deployment. Those actions require separate approval and production capacity,
secret, TLS, monitoring, and retention records.

PyPI publication is deliberately independent from GitHub Release publication.
`.github/workflows/publish-pypi.yml` has only a manual `workflow_dispatch`
trigger and requires an explicit existing stable tag input. Its protected `pypi`
environment and OIDC Trusted Publishing permission remain intact. Dispatching
that workflow requires separate authorization and is outside this release phase.
