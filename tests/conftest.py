from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from auto_bean.common import STATE, TEMPLATE, atomic_write, json_bytes


@pytest.fixture(autouse=True)
def git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_AUTHOR_NAME": "Auto Bean Test",
        "GIT_AUTHOR_EMAIL": "test@example.test",
        "GIT_COMMITTER_NAME": "Auto Bean Test",
        "GIT_COMMITTER_EMAIL": "test@example.test",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def legacy(tmp_path: Path) -> Path:
    root = tmp_path / "legacy ledger"
    shutil.copytree(TEMPLATE, root)
    (root / "AGENTS.md").write_text("# Custom instructions\nKeep my preferences.\n")
    (root / "README.md").write_text("# Custom README\n")
    (root / ".gitignore").write_text(".venv/\nmy-private-file\n")
    paths = {
        ".agents/skills/auto-bean-query/SKILL.md": "custom old query skill",
        ".agents/skills/auto-bean-query/references/custom.md": "custom helper instructions",
        ".agents/skills/shared/workflow-rules.md": "old shared rules",
        ".agents/skills/personal/SKILL.md": "unrelated skill",
        "scripts/validate-ledger.sh": "old script",
        "scripts/personal.sh": "unrelated script",
        ".codex/config.toml": "# User configuration; do not replace\n",
        "statements/raw/raw.csv": "date,amount\n2026-01-01,10\n",
        "statements/parsed/parsed.json": '{"custom":"evidence"}',
        ".venv/preserve": "old environment",
    }
    for relative, content in paths.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root


@pytest.fixture
def current(legacy: Path) -> Path:
    atomic_write(legacy / STATE, json_bytes({"format_version": 1}))
    return legacy
