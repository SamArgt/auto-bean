"""Exercise release gates and publication retries without contacting GitHub."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "plugins/auto-bean/plugin.json"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, text=True, capture_output=True
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-b", "main")
    manifest = root / MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"version": "0.2.1"}))
    git(root, "add", ".")
    git(root, "commit", "-m", "Base version")
    remote = tmp_path / "origin.git"
    git(root, "init", "--bare", str(remote))
    git(root, "remote", "add", "origin", str(remote))
    return root


def checker() -> Any:
    spec = importlib.util.spec_from_file_location(
        "check_plugin_version", ROOT / "scripts/check_plugin_version.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("version", ["0.2.2", "0.2.10", "0.3.0", "1.0.0"])
def test_version_gate_accepts_numeric_increases(repository: Path, version: str) -> None:
    base = git(repository, "rev-parse", "HEAD")
    (repository / MANIFEST).write_text(json.dumps({"version": version}))
    assert version in checker().check_version_increment(base, repository)


@pytest.mark.parametrize(
    "version", ["0.2.1", "0.2.0", "0.1.99", "0.2.2-rc.1", "00.3.0", None]
)
def test_version_gate_rejects_unchanged_lower_or_invalid_versions(
    repository: Path, version: object
) -> None:
    base = git(repository, "rev-parse", "HEAD")
    (repository / MANIFEST).write_text(json.dumps({"version": version}))
    with pytest.raises(ValueError):
        checker().check_version_increment(base, repository)


def test_version_gate_uses_the_supplied_base_commit(repository: Path) -> None:
    first = git(repository, "rev-parse", "HEAD")
    (repository / MANIFEST).write_text(json.dumps({"version": "0.2.2"}))
    git(repository, "commit", "-am", "New base")
    latest = git(repository, "rev-parse", "HEAD")
    assert "0.2.1 -> 0.2.2" in checker().check_version_increment(first, repository)
    with pytest.raises(ValueError, match="must increase"):
        checker().check_version_increment(latest, repository)
    with pytest.raises(ValueError, match="full commit SHA"):
        checker().check_version_increment("--output=unexpected", repository)


@pytest.fixture
def publisher(repository: Path, tmp_path: Path) -> tuple[Path, dict[str, str]]:
    (repository / MANIFEST).write_text(json.dumps({"version": "0.2.2"}))
    git(repository, "commit", "-am", "Release version")
    archive = repository / "dist/auto-bean-0.2.2.zip"
    archive.parent.mkdir()
    archive.write_bytes(b"verified test archive")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    # The workflow uses uv only to read its manifest in this step.
    uv = binaries / "uv"
    uv.write_text(f'#!/bin/bash\nshift 2\nexec "{sys.executable}" "$@"\n')
    uv.chmod(0o755)
    gh = binaries / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "state = Path(os.environ['GH_TEST_STATE'])\n"
        "log = Path(os.environ['GH_TEST_LOG'])\n"
        "args = sys.argv[1:]\n"
        "with log.open('a') as output: output.write(json.dumps(args) + '\\n')\n"
        "saved = json.loads(state.read_text()) if state.exists() else None\n"
        "action = args[1]\n"
        "if action == 'view':\n"
        "    if saved is None: sys.exit(1)\n"
        "    print('true' if saved['draft'] else 'false')\n"
        "elif action in ('create', 'upload'):\n"
        "    assert Path(args[3]).is_file()\n"
        "    if action == 'create':\n"
        "        assert saved is None and '--draft' in args and '--verify-tag' in args\n"
        "        saved = {'draft': True, 'asset': False}\n"
        "    assert saved['draft'], 'Published assets must not be replaced'\n"
        "    state.write_text(json.dumps(saved))\n"
        "    if os.environ.get('GH_FAIL_UPLOAD'): sys.exit(1)\n"
        "    saved['asset'] = True\n"
        "    state.write_text(json.dumps(saved))\n"
        "elif action == 'edit':\n"
        "    assert saved['asset'] and '--draft=false' in args\n"
        "    saved['draft'] = False\n"
        "    state.write_text(json.dumps(saved))\n"
        "else: raise AssertionError(args)\n"
    )
    gh.chmod(0o755)
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/publish-plugin.yml").read_text()
    )
    step = workflow["jobs"]["publish"]["steps"][-1]["run"]
    script = tmp_path / "publish.sh"
    script.write_text(step)
    env = {
        **os.environ,
        "PATH": f"{binaries}{os.pathsep}{os.environ['PATH']}",
        "GH_TEST_STATE": str(tmp_path / "release.json"),
        "GH_TEST_LOG": str(tmp_path / "gh.log"),
        "GITHUB_REF_TYPE": "branch",
        "GITHUB_REF_NAME": "main",
    }
    return script, env


def publish(
    root: Path, publisher: tuple[Path, dict[str, str]]
) -> subprocess.CompletedProcess[str]:
    script, env = publisher
    return subprocess.run(
        ["bash", str(script)], cwd=root, env=env, text=True, capture_output=True
    )


def test_publish_tags_exact_commit_and_leaves_completed_release_unchanged(
    repository: Path, publisher: tuple[Path, dict[str, str]]
) -> None:
    commit = git(repository, "rev-parse", "HEAD")
    result = publish(repository, publisher)
    assert result.returncode == 0, result.stderr
    assert (
        git(repository, "ls-remote", "origin", "refs/tags/v0.2.2").split()[0] == commit
    )
    state = Path(publisher[1]["GH_TEST_STATE"])
    assert json.loads(state.read_text()) == {"draft": False, "asset": True}
    log = Path(publisher[1]["GH_TEST_LOG"])
    before = log.read_text().splitlines()
    result = publish(repository, publisher)
    assert result.returncode == 0, result.stderr
    assert len(log.read_text().splitlines()) == len(before) + 1
    assert "already published" in result.stdout


def test_failed_upload_stays_draft_and_retry_finishes_release(
    repository: Path, publisher: tuple[Path, dict[str, str]]
) -> None:
    publisher[1]["GH_FAIL_UPLOAD"] = "1"
    assert publish(repository, publisher).returncode != 0
    state = Path(publisher[1]["GH_TEST_STATE"])
    assert json.loads(state.read_text()) == {"draft": True, "asset": False}
    del publisher[1]["GH_FAIL_UPLOAD"]
    result = publish(repository, publisher)
    assert result.returncode == 0, result.stderr
    assert json.loads(state.read_text()) == {"draft": False, "asset": True}


def test_existing_tag_on_other_commit_is_never_moved(
    repository: Path, publisher: tuple[Path, dict[str, str]]
) -> None:
    previous = git(repository, "rev-parse", "HEAD^")
    git(repository, "tag", "v0.2.2", previous)
    result = publish(repository, publisher)
    assert result.returncode != 0
    assert "another commit" in result.stderr
    assert git(repository, "rev-parse", "v0.2.2") == previous
    assert not Path(publisher[1]["GH_TEST_LOG"]).exists()


def test_manual_tag_must_match_manifest_version(
    repository: Path, publisher: tuple[Path, dict[str, str]]
) -> None:
    publisher[1].update(GITHUB_REF_TYPE="tag", GITHUB_REF_NAME="v0.2.3")
    result = publish(repository, publisher)
    assert result.returncode != 0
    assert "does not match" in result.stderr
    assert not git(repository, "tag", "--list")
    assert not Path(publisher[1]["GH_TEST_LOG"]).exists()
