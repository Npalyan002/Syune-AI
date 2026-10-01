from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[2]


def test_release_license_is_canonical_and_declared() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("                                 Apache License\n                           Version 2.0, January 2004")
    assert "http://www.apache.org/licenses/" in license_text
    assert "END OF TERMS AND CONDITIONS" in license_text

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE"]


def test_public_release_surfaces_name_apache_2() -> None:
    assert "Apache License 2.0" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Apache License 2.0" in (ROOT / "docs/release/v1.0.0.md").read_text(encoding="utf-8")
