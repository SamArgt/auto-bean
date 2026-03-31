from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from auto_bean.domain.setup import CommandResult, EnvironmentInfo


class PlatformProbe:
    def inspect(self) -> EnvironmentInfo:
        return EnvironmentInfo(
            system=platform.system(),
            release=platform.release(),
            machine=platform.machine(),
            python_version=platform.python_version(),
        )


class CommandRunner:
    def run(self, args: list[str], cwd: Path | None = None) -> CommandResult:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )


class ToolProbe:
    def find(self, command: str) -> str | None:
        return shutil.which(command)


class ProjectPaths:
    def __init__(self, start: Path | None = None) -> None:
        self._start = start or Path.cwd()

    @property
    def repo_root(self) -> Path:
        current = self._start.resolve()
        for candidate in (current, *current.parents):
            if (candidate / "pyproject.toml").is_file() and (candidate / "src").is_dir():
                return candidate
        msg = "Unable to locate the project root from the current working directory."
        raise RuntimeError(msg)

    @property
    def pyproject(self) -> Path:
        return self.repo_root / "pyproject.toml"

    @property
    def venv_directory(self) -> Path:
        return self.repo_root / ".venv"


def current_time() -> float:
    return perf_counter()


def current_python_executable() -> str:
    return sys.executable
