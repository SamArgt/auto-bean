from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from stat import S_IEXEC
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from auto_bean.domain.setup import ArtifactRecord, CommandResult, EnvironmentInfo, WorkflowArtifact


class PlatformInspector(Protocol):
    def inspect(self) -> EnvironmentInfo: ...


class ToolLocator(Protocol):
    def find(self, command: str) -> str | None: ...


class CommandExecutor(Protocol):
    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult: ...


class ArtifactWriter(Protocol):
    def write(self, artifact: ArtifactRecord) -> WorkflowArtifact: ...


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

    @property
    def artifacts_directory(self) -> Path:
        try:
            base_directory = self.repo_root
        except RuntimeError:
            base_directory = self._start.resolve()
        return base_directory / ".auto-bean" / "artifacts"

    @property
    def workspace_template_directory(self) -> Path:
        candidates: list[Path] = []
        try:
            candidates.append(self.repo_root / "workspace_template")
        except RuntimeError:
            pass
        candidates.append(Path(__file__).resolve().parents[3] / "workspace_template")
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0] if candidates else Path("workspace_template")

    def artifact_path(self, run_id: str) -> Path:
        return self.artifacts_directory / f"{run_id}.json"

    def artifact_display_path(self, run_id: str) -> str:
        return f".auto-bean/artifacts/{run_id}.json"


class WorkflowArtifactStore:
    def write(self, artifact: ArtifactRecord) -> WorkflowArtifact:
        artifact_path = Path(artifact.path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps(
                {
                    "run_id": artifact.run_id,
                    "workflow": artifact.workflow,
                    "created_at": artifact.created_at,
                    "result": dict(artifact.result),
                    "events": list(artifact.events),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return WorkflowArtifact(
            artifact_type="workflow-run",
            path=f".auto-bean/artifacts/{artifact_path.name}",
        )


def current_time() -> float:
    return perf_counter()


def current_python_executable() -> str:
    return sys.executable


def current_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def generate_run_id() -> str:
    return uuid4().hex


def sanitize_project_name(project_name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", project_name))


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
