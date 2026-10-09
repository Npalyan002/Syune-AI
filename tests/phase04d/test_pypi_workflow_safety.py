from __future__ import annotations

import re
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
WORKFLOWS = PROJECT / ".github" / "workflows"
PUBLISH = WORKFLOWS / "publish-pypi.yml"


def test_pypi_publication_is_manual_only() -> None:
    text = PUBLISH.read_text(encoding="utf-8")
    trigger = text.split("\njobs:", 1)[0]
    assert "\n  workflow_dispatch:\n" in trigger
    assert "\n      tag:\n" in trigger
    assert "required: true" in trigger
    for automatic in (
        "release:", "push:", "pull_request:", "schedule:",
        "workflow_run:", "repository_dispatch:",
    ):
        assert automatic not in trigger


def test_manual_tag_drives_validation_and_exact_checkout() -> None:
    text = PUBLISH.read_text(encoding="utf-8")
    assert text.count("RELEASE_TAG: ${{ inputs.tag }}") == 2
    assert "ref: ${{ inputs.tag }}" in text
    assert "github.event.release" not in text
    assert "^v[0-9]+\\.[0-9]+\\.[0-9]+$" in text
    assert "release tag/package mismatch" in text
    assert "python -m twine check dist/*" in text


def test_trusted_publishing_stays_job_scoped_and_pinned() -> None:
    text = PUBLISH.read_text(encoding="utf-8")
    assert "environment:\n      name: pypi" in text
    assert text.count("id-token: write") == 1
    assert "contents: write" not in text
    assert "secrets:" not in text
    assert re.search(
        r"pypa/gh-action-pypi-publish@[0-9a-f]{40}(?:\s+#.*)?$", text, re.MULTILINE
    )
    for reference in re.findall(r"^\s*uses:\s*([^\s#]+)", text, re.MULTILINE):
        assert re.search(r"@[0-9a-f]{40}$", reference), reference


def test_no_other_workflow_can_publish_to_pypi() -> None:
    publishing_markers = (
        "gh-action-pypi-publish", "twine upload", "uv publish", "pypi.org/legacy",
    )
    publishers = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8").lower()
        if any(marker in text for marker in publishing_markers):
            publishers.append(path.name)
    assert publishers == [PUBLISH.name]
