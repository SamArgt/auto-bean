from __future__ import annotations

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
    details: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status.value,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
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

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow": self.workflow,
            "status": self.status,
            "error_code": self.error_code,
            "error_category": self.error_category.value
            if self.error_category
            else None,
            "message": self.message,
            "details": self.details,
            "checks": [check.as_dict() for check in self.checks],
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
