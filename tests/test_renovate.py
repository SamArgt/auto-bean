"""Test preparation and merge policy against real Git snapshots."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MESSAGE = "Update dependency\n\nAuto-Bean-Update-Types: patch"


@pytest.fixture
def helper() -> Any:
    spec = importlib.util.spec_from_file_location(
        "renovate", ROOT / "scripts/renovate.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, helper: Any) -> str:
    monkeypatch.chdir(tmp_path)
    helper.git("init", "-b", "main")
    helper.git("config", "user.name", "Renovate Test")
    helper.git("config", "user.email", "test@example.invalid")
    files = {
        helper.MANIFEST: '{"version": "0.2.3"}\n',
        "pyproject.toml": '[project]\nname = "auto-bean-dev"\nversion = "0.2.3"\n[dependency-groups]\ndev = ["ruff>=0.15"]\neval = ["harbor==0.24.0"]\n',
        f"{helper.RUNTIME}/pyproject.toml": '[project]\nname = "auto-bean-runtime"\nversion = "0.2.3"\ndependencies = ["mcp>=1"]\n',
        f"{helper.FRONTEND}/package.json": '{"version": "0.2.3", "dependencies": {"react": "19.1.0"}}\n',
        f"{helper.FRONTEND}/package-lock.json": '{"version": "0.2.3", "packages": {"": {"version": "0.2.3"}, "node_modules/react": {"version": "19.1.0"}}}\n',
        ".github/workflows/test.yml": "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4.1.0\n      - run: echo test\n",
    }
    for path, name in zip(
        helper.LOCKS, ("auto-bean-dev", "auto-bean-runtime"), strict=True
    ):
        files[path] = (
            f'[[package]]\nname = "{name}"\nversion = "0.2.3"\nsource = {{ virtual = "." }}\n[[package]]\nname = "harbor"\nversion = "0.24.0"\nsource = {{ registry = "https://pypi.org/simple" }}\n[[package]]\nname = "httpx"\nversion = "0.28.0"\nsource = {{ registry = "https://pypi.org/simple" }}\n'
        )
    for path, text in files.items():
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    helper.git("add", ".")
    helper.git("commit", "-m", "Base")
    return str(helper.git("rev-parse", "HEAD"))


def change(path: str, old: str, new: str) -> None:
    target = Path(path)
    assert old in target.read_text()
    target.write_text(target.read_text().replace(old, new))


def commit(helper: Any) -> str:
    helper.git("add", ".")
    helper.git("commit", "-m", "Update")
    return str(helper.git("rev-parse", "HEAD"))


def test_preparation_repeat_and_new_base(
    repository: str, helper: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = subprocess.run
    builds: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> Any:
        if args[0] == "npm":
            builds.append(args)
            return subprocess.CompletedProcess(args, 0)
        return original(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    change("uv.lock", 'version = "0.28.0"', 'version = "0.28.1"')
    helper.prepare(repository)
    first = helper.git("diff")
    helper.prepare(repository)
    assert helper.git("diff") == first
    assert json.loads(Path(helper.MANIFEST).read_text())["version"] == "0.2.4"
    assert 'version = "0.28.1"' in Path("uv.lock").read_text()
    assert all(
        "0.2.4" in Path(path).read_text() for path in (*helper.PROJECTS, *helper.LOCKS)
    )
    frontend = json.loads(Path(f"{helper.FRONTEND}/package-lock.json").read_text())
    assert frontend["version"] == frontend["packages"][""]["version"] == "0.2.4"
    helper.prepare(commit(helper))
    assert json.loads(Path(helper.MANIFEST).read_text())["version"] == "0.2.5"
    assert [call[-1] for call in builds] == ["--ignore-scripts", "build"] * 3


@pytest.mark.parametrize(
    ("path", "old", "new", "reason"),
    [
        ("pyproject.toml", "ruff>=0.15", "ruff>=0.16", None),
        ("pyproject.toml", "harbor==0.24.0", "harbor==0.25.0", "eval declarations"),
        ("uv.lock", 'version = "0.24.0"', 'version = "0.25.0"', "eval lock"),
        ("uv.lock", 'version = "0.28.0"', 'version = "0.28.1"', None),
        ("uv.lock", 'version = "0.28.0"', 'version = "1.0.0"', "Major locked"),
        (".github/workflows/test.yml", "checkout@v4.1.0", "checkout@v4.2.0", None),
        (".github/workflows/test.yml", "echo test", "echo changed", "Workflow changes"),
        ("frontend/import-review/package.json", "19.1.0", "19.1.1", None),
    ],
)
def test_actual_diff_policy(
    repository: str, helper: Any, path: str, old: str, new: str, reason: str | None
) -> None:
    change(helper.MANIFEST, "0.2.3", "0.2.4")
    change(path, old, new)
    result = helper.policy_reason(repository, commit(helper), MESSAGE)
    if reason is None:
        assert result is None
    else:
        assert reason in result


@pytest.mark.parametrize("types", ["major", "patch major", "", "unknown"])
def test_major_mixed_unknown(repository: str, helper: Any, types: str) -> None:
    assert (
        helper.policy_reason(repository, repository, f"Auto-Bean-Update-Types: {types}")
        == "Major or unclassified update"
    )


@pytest.mark.parametrize("path", ["evals/harbor/codex.yaml", "scripts/unexpected.py"])
def test_eval_pins_and_unexpected_files(
    repository: str, helper: Any, path: str
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("changed\n")
    assert helper.policy_reason(repository, commit(helper), MESSAGE) is not None


def test_maintenance_checks_direct_eval_versions(repository: str, helper: Any) -> None:
    change("uv.lock", 'version = "0.24.0"', 'version = "0.24.1"')
    assert "eval lock" in helper.policy_reason(
        repository, commit(helper), "Auto-Bean-Update-Types: lockFileMaintenance"
    )


@pytest.mark.parametrize("state", ["failure", "cancelled", "skipped", "pending"])
def test_both_current_checks(helper: Any, state: str) -> None:
    runs = [
        dict(
            id=index,
            name=name,
            app={"slug": "github-actions"},
            head_sha="head",
            status="completed",
            conclusion="success",
        )
        for index, name in enumerate(helper.CHECKS)
    ]
    assert helper.checks_pass(runs, "head")
    assert not helper.checks_pass(runs, "other-head")
    assert not helper.checks_pass(runs[:1], "head")
    runs.append({**runs[0], "id": 9, "conclusion": state})
    assert not helper.checks_pass(runs, "head")


@pytest.mark.parametrize("advanced", [False, True])
def test_merge_checks_base_and_pins_head(
    repository: str, helper: Any, monkeypatch: pytest.MonkeyPatch, advanced: bool
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("RENOVATE_BOT", "renovate-test[bot]")
    change(helper.MANIFEST, "0.2.3", "0.2.4")
    head = commit(helper)
    pr = {
        "number": 1,
        "user": {"login": "renovate-test[bot]"},
        "head": {
            "sha": head,
            "ref": "renovate/test",
            "repo": {"full_name": "owner/repo"},
        },
        "base": {"sha": repository},
        "draft": False,
        "mergeable": True,
    }
    calls: list[tuple[str, tuple[str, ...]]] = []

    def api(path: str, *args: str) -> Any:
        calls.append((path, args))
        if "state=open" in path:
            return [pr]
        if path.endswith("/pulls/1"):
            return pr
        if "/pulls/1/commits" in path:
            return [
                {
                    "sha": head,
                    "author": {"login": "renovate-test[bot]"},
                    "commit": {"message": MESSAGE},
                }
            ]
        if "/check-runs" in path:
            return {
                "check_runs": [
                    dict(
                        id=i,
                        name=name,
                        app={"slug": "github-actions"},
                        head_sha=head,
                        status="completed",
                        conclusion="success",
                    )
                    for i, name in enumerate(helper.CHECKS)
                ]
            }
        if path.endswith("commits/main"):
            return {"sha": "new-base" if advanced else repository}
        if path.endswith("/merge"):
            return {"merged": True}
        raise AssertionError(path)

    monkeypatch.setattr(helper, "api", api)
    original = subprocess.run

    def run(args: list[str], **kwargs: Any) -> Any:
        if args[:2] == ["git", "fetch"]:
            return subprocess.CompletedProcess(args, 0)
        return original(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    helper.merge()
    if advanced:
        assert not any(path.endswith("/merge") for path, _ in calls)
    else:
        assert calls[-1][0].endswith("/merge")
        assert f"sha={head}" in calls[-1][1]
