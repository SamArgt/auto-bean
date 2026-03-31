from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class ErrorCategory(str, Enum):
    VALIDATION_FAILURE = "validation_failure"
    BLOCKED_UNSAFE_MUTATION = "blocked_unsafe_mutation"
    PREREQUISITE_FAILURE = "prerequisite_failure"
    EXECUTION_ERROR = "execution_error"


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: CheckStatus
    message: str
    error_code: str | None = None
    details: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status.value,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class WorkflowEvent:
    run_id: str
    workflow: str
    stage: str
    status: CheckStatus
    message: str
    timestamp: str
    details: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "workflow": self.workflow,
            "stage": self.stage,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass(frozen=True)
class WorkflowArtifact:
    artifact_type: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return {
            "artifact_type": self.artifact_type,
            "path": self.path,
        }


@dataclass(frozen=True)
class WorkflowResult:
    run_id: str
    workflow: str
    status: str
    error_code: str | None
    message: str
    started_at: str
    error_category: ErrorCategory | None = None
    details: dict[str, str] = field(default_factory=dict)
    checks: tuple[DiagnosticCheck, ...] = ()
    events: tuple[WorkflowEvent, ...] = ()
    artifact: WorkflowArtifact | None = None
    duration_seconds: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "workflow": self.workflow,
            "status": self.status,
            "error_code": self.error_code,
            "error_category": self.error_category.value if self.error_category else None,
            "message": self.message,
            "started_at": self.started_at,
            "details": self.details,
            "checks": [check.as_dict() for check in self.checks],
            "events": [event.as_dict() for event in self.events],
            "artifact": self.artifact.as_dict() if self.artifact else None,
            "duration_seconds": round(self.duration_seconds, 3),
        }


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


@dataclass(frozen=True)
class ArtifactRecord:
    run_id: str
    workflow: str
    created_at: str
    path: str
    result: Mapping[str, object]
    events: tuple[dict[str, object], ...]
