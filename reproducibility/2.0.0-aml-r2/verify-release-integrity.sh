#!/usr/bin/env bash
set -euo pipefail

repo="${1:-.}"
implementation="845ef9630435a63c3cc277c6bb27283f6b34906e"
implementation_tree="a6d6f3584769fc9b16bf27e7db2008675ffa8301"
release_root="${repo}/reproducibility/2.0.0-aml-r2"
attestation="${release_root}/immutable-source-attestation.toml"
tmp="$(mktemp -d /tmp/syune-r2-integrity.XXXXXX)"
trap 'rm -rf -- "${tmp}"' EXIT

test "$(git -C "${repo}" rev-parse "${implementation}^{tree}")" = "${implementation_tree}"
git -C "${repo}" archive "${implementation}" | tar -x -C "${tmp}"

(cd "${tmp}" && sha256sum -c "${release_root}/source-manifest.sha256")
(cd "${tmp}" && sha256sum -c "${release_root}/aml09k-source-manifest.sha256")

test "$(sha256sum "${tmp}/uv.lock" | cut -d' ' -f1)" = "e9d4b0db6980a7cc1f4b1d0ed4ca834e05c144e8bbc13bb1acb6e77e026a5b30"
test "$(sha256sum "${tmp}/deploy/aml/Dockerfile" | cut -d' ' -f1)" = "a6cad275008e7d96ff855b8c33a56636d7b2bb0dd6b0547e32d1429cfc4802c5"
test "$(sha256sum "${tmp}/deploy/aml09b1/compose.yaml" | cut -d' ' -f1)" = "d72a5b9a4637e3de8cc913e7ef2ae67199c7c8f3e967fac0bccf8000b97d0fb2"

git -C "${repo}" diff --quiet "${implementation}" -- \
  src tests benchmarks pyproject.toml uv.lock deploy/aml/Dockerfile \
  deploy/aml09b1/compose.yaml deploy/aml09b1/nginx.conf.template \
  deploy/aml09b1/logging.json
git -C "${repo}" diff --check "${implementation}"

attested_hash() {
  sed -n "s/^$1 = \"\([0-9a-f]\{64\}\)\"$/\1/p" "${attestation}"
}
check_attested_file() {
  local key="$1" path="$2" expected actual
  expected="$(attested_hash "${key}")"
  test -n "${expected}"
  actual="$(sha256sum "${path}" | cut -d' ' -f1)"
  test "${actual}" = "${expected}"
}
check_attested_file gitattributes_sha256 "${repo}/.gitattributes"
check_attested_file source_manifest_sha256 "${release_root}/source-manifest.sha256"
check_attested_file aml09k_source_manifest_sha256 "${release_root}/aml09k-source-manifest.sha256"
check_attested_file candidate_manifest_sha256 "${release_root}/candidate-manifest.toml"
check_attested_file aml09k_release_gate_sha256 "${release_root}/aml09k-release-gate.toml"
check_attested_file aml09m_release_gate_sha256 "${release_root}/aml09m-release-gate.toml"
check_attested_file readme_sha256 "${release_root}/README.md"
check_attested_file verification_utility_sha256 "${release_root}/verify-release-integrity.sh"

if git -C "${repo}" grep -nEI '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|Bearer[[:space:]]+[A-Za-z0-9._~+/=-]{16,}|api[_-]?key[[:space:]]*=[[:space:]]*[A-Za-z0-9._~+/=-]{16,})' HEAD -- . ':!*.lock'; then
  echo "high-confidence secret pattern found" >&2
  exit 20
fi

echo "SYUNE_R2_IMMUTABLE_SOURCE_VALID"
