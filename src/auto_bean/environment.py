from __future__ import annotations

import platform
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from stat import S_IEXEC


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class EnvironmentInfo:
    system: str
    release: str
    machine: str
    python_version: str


class PlatformProbe:
    def inspect(self) -> EnvironmentInfo:
        return EnvironmentInfo(
            system=platform.system(),
            release=platform.release(),
            machine=platform.machine(),
            python_version=platform.python_version(),
        )


class ToolProbe:
    def find(self, command: str) -> str | None:
        return shutil.which(command)


class CommandRunner:
    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
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


def ensure_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | S_IEXEC)
