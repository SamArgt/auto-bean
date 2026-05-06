from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class ErrorCategory(str, Enum):
    VALIDATION_FAILURE = "validation_failure"
    BLOCKED_UNSAFE_MUTATION = "blocked_unsafe_mutation"
    PREREQUISITE_FAILURE = "prerequisite_failure"
    EXECUTION_ERROR = "execution_error"


class WorkspaceFileOperation(str, Enum):
    UPDATE = "update"
    REMOVE = "remove"


@dataclass(frozen=True)
class WorkspaceFileChange:
    operation: WorkspaceFileOperation
    path: str
    diff: str
    added_line_count: int
    removed_line_count: int
    source_path: Path | None = None

    @property
    def concerned_line_count(self) -> int:
        return self.added_line_count + self.removed_line_count

    def as_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation.value,
            "path": self.path,
            "source_path": str(self.source_path) if self.source_path else None,
            "added_line_count": self.added_line_count,
            "removed_line_count": self.removed_line_count,
            "concerned_line_count": self.concerned_line_count,
            "diff": self.diff,
        }


@dataclass(frozen=True)
class WorkspaceUpdatePlan:
    changes: tuple[WorkspaceFileChange, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.changes)

    @property
    def updates(self) -> tuple[WorkspaceFileChange, ...]:
        return tuple(
            change
            for change in self.changes
            if change.operation is WorkspaceFileOperation.UPDATE
        )

    @property
    def removals(self) -> tuple[WorkspaceFileChange, ...]:
        return tuple(
            change
            for change in self.changes
            if change.operation is WorkspaceFileOperation.REMOVE
        )

    @property
    def update_paths(self) -> list[str]:
        return [change.path for change in self.updates]

    @property
    def removal_paths(self) -> list[str]:
        return [change.path for change in self.removals]

    @property
    def diffs(self) -> dict[str, str]:
        return {change.path: change.diff for change in self.changes}

    def as_details(self) -> dict[str, object]:
        return {
            "removal_file_count": len(self.removals),
            "removal_paths": self.removal_paths,
            "update_file_count": len(self.updates),
            "update_paths": self.update_paths,
            "changes": [change.as_dict() for change in self.changes],
            "diffs": self.diffs,
        }


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: CheckStatus
    message: str
    error_code: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status.value,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "duration_seconds": round(self.duration_seconds, 3),
        }


@dataclass(frozen=True)
class CommandOutcome:
    workflow: str
    status: str
    error_code: str | None
    error_category: ErrorCategory | None = None
    message: str = ""
    details: dict[str, object] = field(default_factory=dict)
    checks: tuple[DiagnosticCheck, ...] = ()
    duration_seconds: float = 0.0
    update_plan: WorkspaceUpdatePlan | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow": self.workflow,
            "status": self.status,
            "error_code": self.error_code,
            "error_category": self.error_category.value
            if self.error_category is not None
            else None,
            "message": self.message,
            "details": self.details,
            "checks": [check.as_dict() for check in self.checks],
            "duration_seconds": round(self.duration_seconds, 3),
            "update_plan": self.update_plan.as_details()
            if self.update_plan is not None
            else None,
        }


@dataclass(frozen=True)
class InitContext:
    project_name: str
    target_input_type: str
    working_directory: str
    target_directory: str
    template_directory: str
    skill_sources_directory: str

    def as_details(self) -> dict[str, object]:
        return {
            "project_name": self.project_name,
            "target_input_type": self.target_input_type,
            "working_directory": self.working_directory,
            "target_directory": self.target_directory,
            "template_directory": self.template_directory,
            "skill_sources_directory": self.skill_sources_directory,
        }


@dataclass(frozen=True)
class UpdateContext:
    workspace_input: str
    working_directory: str
    target_directory: str
    template_directory: str
    skill_sources_directory: str
    check_only: bool

    def as_details(self) -> dict[str, object]:
        return {
            "workspace_input": self.workspace_input,
            "working_directory": self.working_directory,
            "target_directory": self.target_directory,
            "template_directory": self.template_directory,
            "skill_sources_directory": self.skill_sources_directory,
            "check_only": self.check_only,
        }


type PromptResponder = Callable[[str], str]
type ProgressReporter = Callable[[DiagnosticCheck], None]
type CurrentTaskReporter = Callable[[str], None]
