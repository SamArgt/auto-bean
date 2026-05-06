from __future__ import annotations

import shutil
from difflib import unified_diff
from json import dumps
from pathlib import Path

from auto_bean.environment import ensure_executable
from auto_bean.models import (
    WorkspaceFileChange,
    WorkspaceFileOperation,
    WorkspaceUpdatePlan,
)


class WorkspaceFileManager:
    def scaffold_workspace(
        self,
        *,
        template_directory: Path,
        skill_sources_directory: Path,
        target_directory: Path,
        context7_api_key: str | None,
    ) -> list[str]:
        target_directory.mkdir(parents=True, exist_ok=True)
        created_paths = self.copy_tree(
            source=template_directory,
            destination=target_directory,
        )
        created_paths.extend(
            self.copy_tree(
                source=skill_sources_directory,
                destination=target_directory / ".agents" / "skills",
                prefix=".agents/skills",
            )
        )
        created_paths.extend(self.write_generated_workspace_files(target_directory))
        self.write_context7_config(target_directory, context7_api_key)
        return created_paths

    def copy_tree(
        self, *, source: Path, destination: Path, prefix: str | None = None
    ) -> list[str]:
        created_paths: list[str] = []
        for source_path in sorted(source.rglob("*")):
            relative_path = source_path.relative_to(source)
            destination_path = destination / relative_path
            if source_path.is_dir():
                destination_path.mkdir(parents=True, exist_ok=True)
                continue
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if (
                prefix is None
                and relative_path.parts[:2] == (".auto-bean", "memory")
                and destination_path.exists()
            ):
                continue
            shutil.copy2(source_path, destination_path)
            if destination_path.suffix == ".sh" or "scripts" in relative_path.parts:
                ensure_executable(destination_path)
            path_text = relative_path.as_posix()
            created_paths.append(
                f"{prefix}/{path_text}" if prefix is not None else path_text
            )
        return created_paths

    def planned_workspace_updates(
        self,
        *,
        target_directory: Path,
        template_directory: Path,
        skill_sources_directory: Path,
    ) -> WorkspaceUpdatePlan:
        changes: list[WorkspaceFileChange] = []
        managed_files = [
            (template_directory / "README.md", Path("README.md")),
            (template_directory / "AGENTS.md", Path("AGENTS.md")),
        ]
        managed_files.extend(
            (
                source_path,
                Path(".agents")
                / "skills"
                / source_path.relative_to(skill_sources_directory),
            )
            for source_path in sorted(skill_sources_directory.rglob("*"))
            if source_path.is_file()
        )
        managed_files.extend(
            (
                source_path,
                Path("scripts")
                / source_path.relative_to(template_directory / "scripts"),
            )
            for source_path in sorted((template_directory / "scripts").rglob("*"))
            if source_path.is_file()
        )
        desired_paths = {
            relative_target.as_posix() for _, relative_target in managed_files
        }
        for source_path, relative_target in managed_files:
            target_path = target_directory / relative_target
            source_bytes = source_path.read_bytes()
            target_bytes = target_path.read_bytes() if target_path.exists() else b""
            if target_path.exists() and source_bytes == target_bytes:
                continue
            added_lines, removed_lines = self.line_change_counts(
                source_bytes=source_bytes,
                target_bytes=target_bytes,
            )
            changes.append(
                WorkspaceFileChange(
                    operation=WorkspaceFileOperation.UPDATE,
                    path=relative_target.as_posix(),
                    source_path=source_path,
                    added_line_count=added_lines,
                    removed_line_count=removed_lines,
                    diff=self.file_diff(
                        source_path=source_path,
                        target_path=target_path,
                        relative_path=relative_target.as_posix(),
                    ),
                )
            )
        for relative_target in self.planned_workspace_removals(
            target_directory=target_directory,
            desired_paths=desired_paths,
        ):
            target_path = target_directory / relative_target
            target_bytes = target_path.read_bytes()
            added_lines, removed_lines = self.line_change_counts(
                source_bytes=b"",
                target_bytes=target_bytes,
            )
            changes.append(
                WorkspaceFileChange(
                    operation=WorkspaceFileOperation.REMOVE,
                    path=relative_target.as_posix(),
                    source_path=None,
                    added_line_count=added_lines,
                    removed_line_count=removed_lines,
                    diff=self.file_diff_from_bytes(
                        source_bytes=b"",
                        target_path=target_path,
                        relative_path=relative_target.as_posix(),
                    ),
                )
            )
        return WorkspaceUpdatePlan(tuple(changes))

    def apply_update_plan(
        self, *, target_directory: Path, plan: WorkspaceUpdatePlan
    ) -> None:
        for change in plan.changes:
            target_path = target_directory / change.path
            if change.operation is WorkspaceFileOperation.REMOVE:
                target_path.unlink()
                continue
            if change.source_path is None:
                msg = "Managed workspace update is missing its source path."
                raise TypeError(msg)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(change.source_path, target_path)
            if "scripts" in target_path.relative_to(target_directory).parts:
                ensure_executable(target_path)

    def planned_workspace_removals(
        self, *, target_directory: Path, desired_paths: set[str]
    ) -> list[Path]:
        stale_paths: list[Path] = []
        for managed_root in (Path(".agents") / "skills", Path("scripts")):
            root = target_directory / managed_root
            if not root.exists():
                continue
            for target_path in sorted(root.rglob("*")):
                if not target_path.is_file():
                    continue
                relative_target = target_path.relative_to(target_directory)
                if relative_target.as_posix() in desired_paths:
                    continue
                if self.is_update_removal_excluded(relative_target):
                    continue
                stale_paths.append(relative_target)
        return stale_paths

    def is_update_removal_excluded(self, relative_path: Path) -> bool:
        parts = relative_path.parts
        return (
            relative_path.suffix == ".beancount"
            or parts[:1] == ("beancount",)
            or parts[:1] == ("statement",)
            or parts[:1] == ("statements",)
        )

    def file_diff(
        self, *, source_path: Path, target_path: Path, relative_path: str
    ) -> str:
        return self.file_diff_from_bytes(
            source_bytes=source_path.read_bytes(),
            target_path=target_path,
            relative_path=relative_path,
        )

    def file_diff_from_bytes(
        self, *, source_bytes: bytes, target_path: Path, relative_path: str
    ) -> str:
        source_text = source_bytes.decode("utf-8").splitlines(keepends=True)
        if target_path.exists():
            target_text = target_path.read_text(encoding="utf-8").splitlines(
                keepends=True
            )
        else:
            target_text = []
        return "".join(
            unified_diff(
                target_text,
                source_text,
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
            )
        )

    def line_change_counts(
        self, *, source_bytes: bytes, target_bytes: bytes
    ) -> tuple[int, int]:
        source_lines = source_bytes.decode("utf-8").splitlines()
        target_lines = target_bytes.decode("utf-8").splitlines()
        diff_lines = unified_diff(target_lines, source_lines, lineterm="")
        added_lines = 0
        removed_lines = 0
        for line in diff_lines:
            if line.startswith(("+++", "---")):
                continue
            if line.startswith("+"):
                added_lines += 1
            elif line.startswith("-"):
                removed_lines += 1
        return added_lines, removed_lines

    def write_generated_workspace_files(self, target_directory: Path) -> list[str]:
        self.write_workspace_gitignore(target_directory)
        return [".gitignore"]

    def write_workspace_gitignore(self, target_directory: Path) -> None:
        gitignore_path = target_directory / ".gitignore"
        gitignore_path.write_text(
            ".venv/\n.codex/config.toml\n__pycache__/\n*.pyc\n.DS_Store\n",
            encoding="utf-8",
        )

    def write_context7_config(
        self, target_directory: Path, api_key: str | None
    ) -> None:
        context7_config_path = target_directory / ".codex" / "config.toml"
        context7_config_path.parent.mkdir(parents=True, exist_ok=True)
        if api_key is None:
            header_config = (
                'env_http_headers = { "CONTEXT7_API_KEY" = "CONTEXT7_API_KEY" }'
            )
        else:
            header_config = (
                f'http_headers = {{ "CONTEXT7_API_KEY" = {dumps(api_key)} }}'
            )
        context7_config_path.write_text(
            "[mcp_servers.context7]\n"
            'url = "https://mcp.context7.com/mcp"\n'
            f"{header_config}\n",
            encoding="utf-8",
        )
        context7_config_path.chmod(0o600)
