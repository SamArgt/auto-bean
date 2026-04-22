from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from auto_bean.init import ProjectPaths


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    path: Path


def run_smoke_checks(start: Path | None = None) -> int:
    paths = ProjectPaths(start=start)
    checks = (
        SmokeCheck("workspace guide", paths.workspace_template_directory / "AGENTS.md"),
        SmokeCheck(
            "apply skill",
            paths.skill_sources_directory / "auto-bean-apply" / "SKILL.md",
        ),
        SmokeCheck(
            "apply reconciliation reference",
            paths.skill_sources_directory
            / "auto-bean-apply"
            / "references"
            / "reconciliation-findings.md",
        ),
        SmokeCheck(
            "shared beancount reference",
            paths.skill_sources_directory
            / "shared"
            / "beancount-syntax-and-best-practices.md",
        ),
    )

    missing = [check for check in checks if not check.path.is_file()]
    if missing:
        for check in missing:
            print(f"[FAIL] Missing {check.name}: {check.path}")
        return 1

    for check in checks:
        print(f"[PASS] Found {check.name}: {check.path}")
    return 0
