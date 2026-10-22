from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
from pathlib import Path

from auto_bean.common import (
    PLUGIN,
    WorkflowError,
    atomic_write,
    checked_path,
    digest,
    prerequisites,
    run_checked,
)

EXTRACTION_TOOLS = ("docling", "docling-tools")
TOOLS = ("bean-check", "bean-query", "fava", *EXTRACTION_TOOLS, "bean-price", "python")
BASE_TOOLS = tuple(tool for tool in TOOLS if tool not in EXTRACTION_TOOLS)


def fingerprint(plugin: Path = PLUGIN, *, extraction: bool = False) -> str:
    runtime = plugin / "runtime"
    return digest(
        (runtime / "pyproject.toml").read_bytes()
        + b"\0"
        + (runtime / "uv.lock").read_bytes()
        + (b"\0extraction" if extraction else b"")
    )[:24]


def healthy(environment: Path, *, extraction: bool = False) -> bool:
    tools = TOOLS if extraction else BASE_TOOLS
    if not all((environment / "bin" / tool).is_file() for tool in tools):
        return False
    result = subprocess.run(
        [
            str(environment / "bin/python"),
            "-c",
            "import beancount, beanquery, fava, beanprice, jsonschema, yaml, mcp"
            + (", docling" if extraction else ""),
        ],
        capture_output=True,
    )
    return result.returncode == 0


def ensure_runtime(
    root: Path, *, plugin: Path = PLUGIN, extraction: bool = False
) -> Path:
    """Build each dependency generation in place, never relocate a venv's shebangs."""
    prerequisites()
    key = fingerprint(plugin, extraction=extraction)
    directory = checked_path(root, f".auto-bean/runtime/{key}")
    directory.mkdir(parents=True, exist_ok=True)
    environment = checked_path(root, f".auto-bean/runtime/{key}/.venv")
    marker = checked_path(root, f".auto-bean/runtime/{key}/ready")
    lock = checked_path(root, f".auto-bean/runtime/{key}/prepare.lock")
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        if (
            marker.is_file()
            and marker.read_text() == key
            and healthy(environment, extraction=extraction)
        ):
            return environment
        # This generation is either unprepared or broken. Other hashes remain untouched.
        marker.unlink(missing_ok=True)
        if environment.exists():
            shutil.rmtree(environment)
        env = dict(
            os.environ,
            UV_PROJECT_ENVIRONMENT=str(environment),
            PYTHONDONTWRITEBYTECODE="1",
        )
        try:
            run_checked(
                [
                    "uv",
                    "sync",
                    "--project",
                    str(plugin / "runtime"),
                    "--frozen",
                    "--no-dev",
                    *(["--extra", "extraction"] if extraction else []),
                ],
                cwd=root,
                env=env,
            )
            if not healthy(environment, extraction=extraction):
                raise WorkflowError(
                    "runtime_unhealthy",
                    "Installed runtime failed its tool/import checks.",
                )
        except (WorkflowError, OSError):
            shutil.rmtree(environment, ignore_errors=True)
            raise
        atomic_write(marker, key.encode())
    return environment


def validate(root: Path, environment: Path) -> None:
    run_checked([str(environment / "bin/bean-check"), "ledger.beancount"], cwd=root)


def run_tool(root: Path, tool: str, args: list[str]) -> int:
    if tool not in TOOLS:
        raise WorkflowError("unsupported_tool", f"Unsupported runtime tool: {tool}")
    environment = ensure_runtime(root, extraction=tool in EXTRACTION_TOOLS)
    env = dict(os.environ, VIRTUAL_ENV=str(environment), PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = str(PLUGIN / "runtime")
    env["PATH"] = str(environment / "bin") + os.pathsep + env.get("PATH", "")
    # exec retains streaming output, signals, exit status, and background-session behavior.
    os.chdir(root)
    os.execve(environment / "bin" / tool, [tool, *args], env)
    return 1  # pragma: no cover - exec only returns by raising


def serve() -> int:
    """Prepare a plugin-owned cache without requiring a ledger workspace."""
    cache = (
        Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
        / "auto-bean-service"
    )
    cache.mkdir(parents=True, exist_ok=True)
    if cache.is_symlink():
        raise WorkflowError("unsafe_path", "Service cache must not be a symlink.")
    environment = ensure_runtime(cache)
    env = dict(
        os.environ,
        VIRTUAL_ENV=str(environment),
        PYTHONPATH=str(PLUGIN / "runtime"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    env["PATH"] = str(environment / "bin") + os.pathsep + env.get("PATH", "")
    interpreter = environment / "bin/python"
    os.execve(interpreter, [str(interpreter), "-m", "auto_bean.server"], env)
    return 1
