# AML cloud container validation

The manual GitHub Actions workflow at
`.github/workflows/aml-container-validation.yml` replaces local Docker Desktop
validation. Merely adding this file does not execute it, and no container result
may be reported as passed until a completed run is reviewed.

## Execution prerequisites

1. Commit the complete proposed `1.1.1-aml.1` source tree to a private or
   appropriately controlled GitHub branch. Do not reuse the historical
   `v1.1.0` tag.
2. Enable GitHub Actions and allow GitHub-hosted `ubuntu-24.04` runners for the
   repository. The job needs Docker Engine, Docker Compose v2, OpenSSL, curl,
   and at least the standard hosted-runner disk and memory allocation.
3. Permit outbound HTTPS to GitHub action distribution, Docker Hub, PyPI, and
   Python package indexes used by the locked environment.
4. Keep workflow permissions at `contents: read`. No environments, repository
   secrets, OIDC tokens, package writes, artifacts, caches, or privileged
   third-party actions are required.
5. Manually dispatch **SYUNE v1.1 cross-platform acceptance** for the exact
   candidate ref. GitHub requires a dispatch target to exist on the default
   branch, so the candidate version of that already-registered workflow invokes
   the reusable **AML container release-candidate validation** workflow. Its AML
   job is explicitly guarded to `workflow_dispatch`; push and pull-request runs
   cannot invoke the container validation. Record the source commit and workflow
   run URL in the release evidence.

The only actions are pinned to immutable commits already reviewed in the
repository's release workflow:

- `actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803` (`v6`)
- `actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1` (`v6`)

## Validation plan

The job checks the dependency hashes and OCI digest pins, renders Compose,
installs the frozen Python environment, and runs the complete regression suite.
It then builds the application image with `--pull`, inspects its user and layers,
starts the digest-pinned Nginx stack, and verifies:

- non-root UID/GID 10001 and a read-only application filesystem;
- CPU, memory, PID, capability, and `no-new-privileges` controls;
- writable named evaluation volume with private application ownership;
- `nginx -t`, HTTPS health, and public readiness isolation;
- authenticated Add/Search, exact replay, conflicting replay, and sanitized
  invalid requests;
- 100 eligible native results without changing ranking;
- stop/start health transition, SQLite persistence, and concurrent Add/Search;
- request-body rejection, rate limiting, and `Retry-After`;
- absence of the synthetic bearer token and payload marker from image history,
  image layers, rendered Compose configuration, and runtime logs.

The job removes its containers, named volume, certificate, token, and temporary
files even after failure. It uploads no logs, databases, images, or artifacts.

## Synthetic-data and logging controls

The bearer token is randomly generated inside the runner and registered with
GitHub's masking command. A mode-`0600` runner-owned copy is used by the client
probe; a separate mode-`0400`, UID/GID-`10001` copy is mounted by Compose so the
non-root application can read it without broadening file permissions. The
one-day self-signed certificate is also runner-local. Neither value is a GitHub
secret or production credential.

Test messages contain only a fixed synthetic marker. Application and proxy logs
remain metadata-only. The workflow scans logs and image material, then deletes
the scan files instead of uploading them. Operators must not enable shell
tracing, add payload-printing diagnostics, or upload failure-state volumes.

## Review and promotion

A successful green job is necessary but not sufficient for deployment. Review
the source SHA, runner image, action SHAs, image digests, every step result, and
cleanup completion. Any rerun after a source or deployment-file change is a new
validation. Public deployment, AML Smoke/Full execution, tags, and releases all
remain separate approval gates.
