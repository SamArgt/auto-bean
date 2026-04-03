from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from stat import S_IEXEC
from time import perf_counter
from typing import Protocol

from auto_bean.domain.setup import (
    CommandResult,
    EnvironmentInfo,
)


class PlatformInspector(Protocol):
    def inspect(self) -> EnvironmentInfo: ...


class ToolLocator(Protocol):
    def find(self, command: str) -> str | None: ...


class CommandExecutor(Protocol):
    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult: ...


type PromptResponder = Callable[[str], str]


class PlatformProbe:
    def inspect(self) -> EnvironmentInfo:
        return EnvironmentInfo(
            system=platform.system(),
            release=platform.release(),
            machine=platform.machine(),
            python_version=platform.python_version(),
        )


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


class ToolProbe:
    def find(self, command: str) -> str | None:
        return shutil.which(command)


class ProjectPaths:
    def __init__(self, start: Path | None = None) -> None:
        self._start = start or Path.cwd()

    @property
    def working_directory(self) -> Path:
        return self._start.resolve()

    @property
    def repo_root(self) -> Path:
        current = self._start.resolve()
        for candidate in (current, *current.parents):
            if (candidate / "pyproject.toml").is_file() and (
                candidate / "src"
            ).is_dir():
                return candidate
        msg = "Unable to locate the project root from the current working directory."
        raise RuntimeError(msg)

    @property
    def pyproject(self) -> Path:
        return self.repo_root / "pyproject.toml"

    @property
    def venv_directory(self) -> Path:
        return self.repo_root / ".venv"

    @property
    def workspace_template_directory(self) -> Path:
        candidates: list[Path] = []
        try:
            candidates.append(self.repo_root / "workspace_template")
        except RuntimeError:
            pass
        for resource_root in self.resource_roots:
            candidates.append(resource_root / "workspace_template")
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0] if candidates else Path("workspace_template")

    @property
    def skill_sources_directory(self) -> Path:
        candidates: list[Path] = []
        try:
            candidates.append(self.repo_root / "skill_sources")
        except RuntimeError:
            pass
        for resource_root in self.resource_roots:
            candidates.append(resource_root / "skill_sources")
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0] if candidates else Path("skill_sources")

    @property
    def installed_resources_directory(self) -> Path:
        return Path(__file__).resolve().parents[1] / "_packaged_assets"

    @property
    def source_checkout_resources_directory(self) -> Path:
        module_path = Path(__file__).resolve()
        for parent in module_path.parents:
            if (parent / "workspace_template").is_dir() and (
                parent / "skill_sources"
            ).is_dir():
                return parent
        return module_path.parents[1]

    @property
    def resource_roots(self) -> tuple[Path, ...]:
        roots: list[Path] = []
        for candidate in (
            self.installed_resources_directory,
            self.source_checkout_resources_directory,
        ):
            if candidate not in roots:
                roots.append(candidate)
        return tuple(roots)


def current_time() -> float:
    return perf_counter()


def current_python_executable() -> str:
    return sys.executable


def sanitize_project_name(project_name: str) -> bool:
    return bool(
        re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", project_name)
    )


def looks_like_path(target: str) -> bool:
    path = Path(target).expanduser()
    return (
        path.is_absolute()
        or len(path.parts) > 1
        or target.startswith((".", "~"))
        or target.endswith(("/", "\\"))
    )


def ensure_executable(path: Path) -> None:
    current_mode = path.stat().st_mode
    path.chmod(current_mode | S_IEXEC)


def copy_workspace_template(template_dir: Path, target_dir: Path) -> list[str]:
    created_paths: list[str] = []
    for source in sorted(template_dir.rglob("*")):
        relative_path = source.relative_to(template_dir)
        destination = target_dir / relative_path
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if destination.suffix == ".sh":
            ensure_executable(destination)
        created_paths.append(relative_path.as_posix())
    return created_paths


def copy_skill_sources(skill_sources_dir: Path, target_dir: Path) -> list[str]:
    created_paths: list[str] = []
    for source in sorted(skill_sources_dir.rglob("*")):
        relative_path = source.relative_to(skill_sources_dir)
        destination = target_dir / relative_path
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if "scripts" in relative_path.parts:
            ensure_executable(destination)
        created_paths.append(relative_path.as_posix())
    return created_paths
