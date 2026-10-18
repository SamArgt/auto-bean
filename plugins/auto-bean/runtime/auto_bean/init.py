from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from auto_bean.common import (
    FORMAT_VERSION,
    STATE,
    TEMPLATE,
    WorkflowError,
    atomic_write,
    ignore_contents,
    json_bytes,
    prerequisites,
    run_checked,
    digest,
)
from auto_bean.runtime import ensure_runtime, validate


def initialize(target: Path) -> dict[str, object]:
    prerequisites(git=True)
    # Inspect the supplied path before resolving it so an existing symlink is rejected.
    target = target.expanduser().absolute()
    if target.is_symlink():
        raise WorkflowError("unsafe_target", "The destination must not be a symlink.")
    root = target.resolve()
    if root == Path(root.anchor):
        raise WorkflowError(
            "unsafe_target", "The filesystem root cannot be a ledger workspace."
        )
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise WorkflowError(
            "non_empty_target",
            "Choose an empty destination; use $auto-bean:auto-bean-migrate for an existing ledger.",
        )
    if not (TEMPLATE / "ledger.beancount").is_file():
        raise WorkflowError(
            "missing_assets", "The installed plugin has no workspace template."
        )
    existed = root.exists()
    root.mkdir(parents=True, exist_ok=True)
    created: dict[Path, str] = {}
    try:
        shutil.copytree(TEMPLATE, root, dirs_exist_ok=True)
        # A plugin cache may be read-only. Its permissions must not become ledger permissions.
        root.chmod(root.stat().st_mode | 0o700)
        for path in root.rglob("*"):
            path.chmod(0o700 if path.is_dir() else 0o600)
        for relative in ("statements/raw", "statements/parsed"):
            (root / relative).mkdir(parents=True, exist_ok=True)
            (root / relative / ".gitkeep").touch()
        atomic_write(root / ".gitignore", ignore_contents(root))
        atomic_write(root / STATE, json_bytes({"format_version": FORMAT_VERSION}))
        created = {
            path: digest(path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        }
        run_checked(["git", "init"], cwd=root)
        environment = ensure_runtime(root)
        validate(root, environment)
    except Exception:
        # Delete only our unchanged scaffold and generated runtime. Preserve concurrent user writes.
        for path, original in created.items():
            if (
                not path.is_symlink()
                and path.is_file()
                and digest(path.read_bytes()) == original
            ):
                path.unlink()
        for relative in (".auto-bean/runtime", ".git"):
            generated = root / relative
            if generated.is_dir() and not generated.is_symlink():
                # Never discard history created while initialization was running.
                if relative == ".git" and any(
                    path.is_file() for path in (generated / "refs").rglob("*")
                ):
                    continue
                shutil.rmtree(generated)
        for directory in sorted(
            root.rglob("*"), key=lambda p: len(p.parts), reverse=True
        ):
            if (
                directory.is_dir()
                and not directory.is_symlink()
                and not any(directory.iterdir())
            ):
                directory.rmdir()
        if not existed and not any(root.iterdir()):
            root.rmdir()
        raise
    identity = subprocess.run(
        ["git", "var", "GIT_AUTHOR_IDENT"], cwd=root, capture_output=True, text=True
    )
    if identity.returncode:
        return {
            "status": "needs_input",
            "workspace": str(root),
            "validated": True,
            "message": "Workspace is ready. Configure Git identity, then ask Codex to create its initial commit.",
        }
    run_checked(["git", "add", "--all"], cwd=root)
    try:
        run_checked(["git", "commit", "-m", "Initialize auto-bean ledger"], cwd=root)
    except WorkflowError as error:
        return {
            "status": "needs_input",
            "workspace": str(root),
            "validated": True,
            "message": f"Workspace is ready; initial commit needs attention: {error}",
        }
    return {
        "status": "ok",
        "workspace": str(root),
        "validated": True,
        "message": "Ledger initialized. Use $auto-bean:auto-bean-import, $auto-bean:auto-bean-query, or $auto-bean:auto-bean-write.",
    }
