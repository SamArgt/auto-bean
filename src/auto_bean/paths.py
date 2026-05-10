from __future__ import annotations

import re
from pathlib import Path


class ProjectPaths:
    def __init__(self, start: Path | None = None) -> None:
        self._start = (start or Path.cwd()).resolve()

    @property
    def working_directory(self) -> Path:
        return self._start

    @property
    def repo_root(self) -> Path:
        for candidate in (self._start, *self._start.parents):
            if (candidate / "pyproject.toml").is_file() and (
                candidate / "src"
            ).is_dir():
                return candidate
        msg = "Unable to locate the project root from the current working directory."
        raise RuntimeError(msg)

    @property
    def installed_resources_directory(self) -> Path:
        return Path(__file__).resolve().parent / "_packaged_assets"

    @property
    def source_checkout_resources_directory(self) -> Path:
        module_path = Path(__file__).resolve()
        for parent in module_path.parents:
            if (parent / "workspace_template").is_dir() and (
                parent / "skill_sources"
            ).is_dir():
                return parent
        return module_path.parent

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

    @property
    def workspace_template_directory(self) -> Path:
        return self._resolve_resource_directory("workspace_template")

    @property
    def skill_sources_directory(self) -> Path:
        return self._resolve_resource_directory("skill_sources")

    def _resolve_resource_directory(self, name: str) -> Path:
        candidates: list[Path] = []
        try:
            candidates.append(self.repo_root / name)
        except RuntimeError:
            pass
        candidates.extend(root / name for root in self.resource_roots)
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0] if candidates else Path(name)


def resolve_target_directory(
    paths: ProjectPaths, project_name: str
) -> tuple[Path, str]:
    if looks_like_path(project_name):
        return (
            (paths.working_directory / Path(project_name).expanduser()).resolve(),
            "path",
        )

    try:
        repo_root = paths.repo_root
    except RuntimeError:
        return ((paths.working_directory / project_name).resolve(), "name")

    if (
        paths.working_directory == repo_root
        or repo_root in paths.working_directory.parents
    ):
        return ((repo_root.parent / project_name).resolve(), "name")
    return ((paths.working_directory / project_name).resolve(), "name")


def resolve_workspace_directory(paths: ProjectPaths, workspace: str) -> Path:
    path = Path(workspace).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (paths.working_directory / path).resolve()


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
