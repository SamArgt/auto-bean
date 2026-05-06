from __future__ import annotations

import shutil
from pathlib import Path

from auto_bean.init import WorkspaceUpdateService, build_workspace_update_service


def _scaffold_current_workspace(
    service: WorkspaceUpdateService, workspace: Path
) -> None:
    shutil.copytree(service.paths.workspace_template_directory, workspace)
    shutil.copytree(
        service.paths.skill_sources_directory,
        workspace / ".agents" / "skills",
    )
    service.workspace_files.write_generated_workspace_files(workspace)


def test_update_check_discovers_stale_managed_files(tmp_path: Path) -> None:
    service = build_workspace_update_service()
    workspace = tmp_path / "workspace"
    _scaffold_current_workspace(service, workspace)
    stale_skill = workspace / ".agents" / "skills" / "retired-skill" / "SKILL.md"
    stale_script = workspace / "scripts" / "retired-helper.sh"
    excluded_beancount = workspace / "scripts" / "retired.beancount"
    stale_skill.parent.mkdir(parents=True)
    stale_skill.write_text("retired skill\n", encoding="utf-8")
    stale_script.write_text("#!/bin/sh\n", encoding="utf-8")
    excluded_beancount.write_text("2026-01-01 open Assets:Cash\n", encoding="utf-8")

    result = service.update(str(workspace), check_only=True)

    assert result.status == "updates_available"
    assert result.update_plan is not None
    assert result.details["removal_file_count"] == 2
    assert result.details["removal_paths"] == [
        ".agents/skills/retired-skill/SKILL.md",
        "scripts/retired-helper.sh",
    ]
    assert [change.removed_line_count for change in result.update_plan.removals] == [
        1,
        1,
    ]
    assert stale_skill.exists()
    assert stale_script.exists()
    assert excluded_beancount.exists()


def test_update_removes_stale_managed_files(tmp_path: Path) -> None:
    service = build_workspace_update_service()
    workspace = tmp_path / "workspace"
    _scaffold_current_workspace(service, workspace)
    stale_skill = workspace / ".agents" / "skills" / "retired-skill" / "SKILL.md"
    stale_script = workspace / "scripts" / "retired-helper.sh"
    excluded_beancount = workspace / "scripts" / "retired.beancount"
    stale_skill.parent.mkdir(parents=True)
    stale_skill.write_text("retired skill\n", encoding="utf-8")
    stale_script.write_text("#!/bin/sh\n", encoding="utf-8")
    excluded_beancount.write_text("2026-01-01 open Assets:Cash\n", encoding="utf-8")

    result = service.update(str(workspace))

    assert result.status == "ok"
    assert result.update_plan is not None
    assert result.details["removal_file_count"] == 2
    assert result.details["removal_paths"] == [
        ".agents/skills/retired-skill/SKILL.md",
        "scripts/retired-helper.sh",
    ]
    assert not stale_skill.exists()
    assert not stale_script.exists()
    assert excluded_beancount.exists()
