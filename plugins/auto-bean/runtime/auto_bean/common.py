from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1
PLUGIN = Path(__file__).resolve().parents[2]
TEMPLATE = PLUGIN / "assets" / "workspace_template"
STATE = ".auto-bean/workspace.json"
IGNORE_LINES = (
    ".auto-bean/runtime/",
    ".auto-bean/migrations/",
    ".auto-bean/tmp/",
    ".venv/",
    ".codex/config.toml",
    "__pycache__/",
    "*.pyc",
    ".DS_Store",
)


class WorkflowError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise WorkflowError("invalid_state", f"Expected a JSON object: {path}")
    return value


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def checked_path(root: Path, relative: str) -> Path:
    """Do not traverse workspace symlinks or accept paths outside its root."""
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or ".." in parts:
        raise WorkflowError("unsafe_path", f"Unsafe workspace path: {relative}")
    current = root
    for part in parts:
        current /= part
        if current.is_symlink():
            raise WorkflowError("unsafe_path", f"Refusing symlink: {current}")
    return current


def workspace(path: Path, *, legacy: bool = False) -> Path:
    root = path.expanduser().resolve()
    if not root.is_dir() or not checked_path(root, "ledger.beancount").is_file():
        raise WorkflowError("not_workspace", f"No ledger.beancount in {root}")
    checked_path(root, ".auto-bean")
    marker = checked_path(root, STATE)
    if marker.exists():
        if read_json(marker).get("format_version") != FORMAT_VERSION:
            raise WorkflowError(
                "unsupported_format",
                "This workspace requires a compatible plugin release.",
            )
    elif not legacy:
        raise WorkflowError(
            "migration_required",
            "Run $auto-bean:auto-bean-migrate before operating this ledger.",
        )
    elif not checked_path(root, ".auto-bean/memory").is_dir():
        raise WorkflowError(
            "not_workspace", "Missing auto-bean governed memory directory."
        )
    if not legacy:
        migrations = checked_path(root, ".auto-bean/migrations")
        if migrations.is_dir():
            for journal in migrations.glob("*/journal.json"):
                checked_path(root, journal.relative_to(root).as_posix())
                if read_json(journal).get("status") != "complete":
                    raise WorkflowError(
                        "migration_incomplete",
                        "Resume the unfinished migration before operating this ledger.",
                    )
    return root


def prerequisites(*, git: bool = False) -> None:
    if platform.system() not in {"Darwin", "Linux"}:
        raise WorkflowError(
            "unsupported_platform", "Only macOS and Linux are supported."
        )
    for name in ("uv", "git") if git else ("uv",):
        if shutil.which(name) is None:
            raise WorkflowError(
                "missing_prerequisite", f"Install {name} before continuing."
            )


def run_checked(
    args: Sequence[str], *, cwd: Path, env: dict[str, str] | None = None
) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode:
        # Financial tool diagnostics belong in the current conversation, never telemetry.
        raise WorkflowError(
            "command_failed",
            f"{args[0]} exited {result.returncode}: {result.stderr.strip()[-4000:]}",
        )
    return result.stdout.strip()


def ignore_contents(root: Path) -> bytes:
    path = checked_path(root, ".gitignore")
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = original.splitlines()
    missing = [line for line in IGNORE_LINES if line not in lines]
    if not missing:
        return original.encode()
    return (
        (original.rstrip("\n") + "\n" + "\n".join(missing) + "\n").lstrip("\n").encode()
    )
