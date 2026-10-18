from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def packaging() -> Any:
    spec = importlib.util.spec_from_file_location(
        "package_plugin", ROOT / "scripts/package_plugin.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_archive_is_reproducible_self_contained_and_matches_canonical_sources(
    tmp_path: Path,
) -> None:
    module = packaging()
    first = module.package_plugin(tmp_path / "first.zip")
    second = module.package_plugin(tmp_path / "second.zip")
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert "plugin.json" in names
        assert "runtime/uv.lock" in names
        assert "assets/workspace_template/.auto-bean/memory/MEMORY.md" in names
        assert not any("__pycache__" in name or ".venv" in name for name in names)
        assert len([name for name in names if name.endswith("/SKILL.md")]) == 9
        for name in names:
            assert archive.read(name) == (module.PLUGIN / name).read_bytes()


def test_marketplace_points_to_canonical_plugin_directory() -> None:
    catalog = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    entry = catalog["plugins"][0]
    assert entry["name"] == "auto-bean"
    assert (ROOT / entry["source"]["path"]).resolve() == ROOT / "plugins/auto-bean"
    assert entry["policy"]["installation"] == "AVAILABLE"


def test_manifest_and_packaged_references_are_valid() -> None:
    assert packaging().validate_plugin() == "0.2.0"
