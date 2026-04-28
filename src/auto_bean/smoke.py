from __future__ import annotations

from collections.abc import Callable

from auto_bean.cli import main


def run_smoke_checks() -> int:
    checks: tuple[tuple[str, Callable[[], bool]], ...] = (
        ("cli_help", lambda: main(["--help"]) == 0),
        ("init_help", lambda: main(["init", "--help"]) == 0),
    )
    failed: list[str] = []
    for name, check in checks:
        if not check():
            failed.append(name)

    if failed:
        print("Smoke checks failed: " + ", ".join(failed))
        return 1
    print("Smoke checks passed.")
    return 0
