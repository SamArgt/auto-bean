from __future__ import annotations

from pathlib import Path

from auto_bean.smoke import run_smoke_checks


def test_run_smoke_checks_passes_for_repo_assets() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert run_smoke_checks(start=repo_root) == 0
