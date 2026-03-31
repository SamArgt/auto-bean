from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from auto_bean.domain.setup import CheckStatus, DiagnosticCheck, WorkflowResult
from auto_bean.infrastructure.setup import (
    CommandRunner,
    PlatformProbe,
    ProjectPaths,
    ToolProbe,
    current_time,
)


REQUIRED_DEPENDENCIES = ("beancount", "fava")
DEPENDENCY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass
class SetupService:
    paths: ProjectPaths
    platform_probe: PlatformProbe
    tool_probe: ToolProbe
    command_runner: CommandRunner

    def bootstrap(self) -> WorkflowResult:
        started = current_time()
        environment_check = self._check_supported_environment()
        uv_check = self._check_uv_available()
        if environment_check.status is CheckStatus.FAIL:
            return self._result(
                status="failed",
                error_code=environment_check.error_code,
                message=environment_check.message,
                details=environment_check.details,
                checks=(environment_check, uv_check),
                started=started,
            )
        if uv_check.status is CheckStatus.FAIL:
            return self._result(
                status="failed",
                error_code=uv_check.error_code,
                message=uv_check.message,
                details=uv_check.details,
                checks=(environment_check, uv_check),
                started=started,
            )

        dependency_check = self._check_declared_dependencies()
        if dependency_check.status is CheckStatus.FAIL:
            return self._result(
                status="failed",
                error_code=dependency_check.error_code,
                message=dependency_check.message,
                details=dependency_check.details,
                checks=(environment_check, uv_check, dependency_check),
                started=started,
            )
        sync_result = self.command_runner.run(["uv", "sync"], cwd=self.paths.repo_root)
        sync_check = self._build_uv_sync_check(sync_result)
        import_check = self._run_import_check()
        checks = (
            environment_check,
            uv_check,
            dependency_check,
            sync_check,
            import_check,
        )
        failed_check = next((check for check in checks if check.status is CheckStatus.FAIL), None)
        if failed_check is not None:
            return self._result(
                status="failed",
                error_code=failed_check.error_code,
                message=failed_check.message,
                details=failed_check.details,
                checks=checks,
                started=started,
            )
        return self._result(
            status="ok",
            error_code=None,
            message="Bootstrap completed successfully.",
            details={"repo_root": str(self.paths.repo_root)},
            checks=checks,
            started=started,
        )

    def readiness(self) -> WorkflowResult:
        started = current_time()
        checks = (
            self._check_supported_environment(),
            self._check_uv_available(),
            self._check_virtual_environment(),
            self._check_declared_dependencies(),
            self._run_import_check(),
            self._run_entrypoint_check(),
            self._run_tool_command_check("fava", ["--version"], "fava_cli", "fava"),
            self._run_tool_command_check(
                "bean-check",
                ["--help"],
                "beancount_cli",
                "bean-check",
            ),
        )
        failed_check = next((check for check in checks if check.status is CheckStatus.FAIL), None)
        if failed_check is not None:
            return self._result(
                status="failed",
                error_code=failed_check.error_code,
                message=failed_check.message,
                details=failed_check.details,
                checks=checks,
                started=started,
            )
        return self._result(
            status="ok",
            error_code=None,
            message="Readiness check passed.",
            details={"repo_root": str(self.paths.repo_root)},
            checks=checks,
            started=started,
        )

    def _check_supported_environment(self) -> DiagnosticCheck:
        environment = self.platform_probe.inspect()
        if environment.system != "Darwin":
            return DiagnosticCheck(
                name="supported_environment",
                status=CheckStatus.FAIL,
                error_code="unsupported_environment",
                message="auto-bean bootstrap/readiness currently supports macOS only.",
                details={
                    "detected_system": environment.system,
                    "detected_release": environment.release,
                    "detected_machine": environment.machine,
                    "remediation": "Run this workflow on a supported macOS machine.",
                },
            )
        return DiagnosticCheck(
            name="supported_environment",
            status=CheckStatus.PASS,
            error_code=None,
            message="Supported macOS environment detected.",
            details={
                "detected_system": environment.system,
                "detected_release": environment.release,
                "detected_machine": environment.machine,
                "python_version": environment.python_version,
            },
        )

    def _check_uv_available(self) -> DiagnosticCheck:
        uv_path = self.tool_probe.find("uv")
        if uv_path is None:
            return DiagnosticCheck(
                name="uv_available",
                status=CheckStatus.FAIL,
                error_code="missing_uv",
                message="The 'uv' command is required but was not found.",
                details={
                    "remediation": "Install uv, then rerun bootstrap. Example: https://docs.astral.sh/uv/getting-started/installation/",
                },
            )
        return DiagnosticCheck(
            name="uv_available",
            status=CheckStatus.PASS,
            error_code=None,
            message="uv is available.",
            details={"path": uv_path},
        )

    def _check_virtual_environment(self) -> DiagnosticCheck:
        venv_directory = self.paths.venv_directory
        if not venv_directory.is_dir():
            return DiagnosticCheck(
                name="uv_environment",
                status=CheckStatus.FAIL,
                error_code="missing_uv_environment",
                message="The repo-local uv environment has not been created yet.",
                details={
                    "expected_path": str(venv_directory),
                    "remediation": "Run 'auto-bean bootstrap' to create and sync the project environment.",
                },
            )
        return DiagnosticCheck(
            name="uv_environment",
            status=CheckStatus.PASS,
            error_code=None,
            message="Repo-local uv environment is present.",
            details={"path": str(venv_directory)},
        )

    def _check_declared_dependencies(self) -> DiagnosticCheck:
        try:
            with self.paths.pyproject.open("rb") as handle:
                pyproject = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            return DiagnosticCheck(
                name="declared_dependencies",
                status=CheckStatus.FAIL,
                error_code="invalid_pyproject",
                message="pyproject.toml could not be read as valid TOML.",
                details={
                    "path": str(self.paths.pyproject),
                    "error": str(exc),
                    "remediation": "Fix pyproject.toml so it is readable TOML, then rerun bootstrap.",
                },
            )
        dependencies = pyproject.get("project", {}).get("dependencies", [])
        normalized_dependencies = {
            normalized
            for entry in dependencies
            if isinstance(entry, str)
            for normalized in [self._normalize_dependency_name(entry)]
            if normalized is not None
        }
        missing = [
            dependency
            for dependency in REQUIRED_DEPENDENCIES
            if dependency not in normalized_dependencies
        ]
        if missing:
            return DiagnosticCheck(
                name="declared_dependencies",
                status=CheckStatus.FAIL,
                error_code="missing_declared_dependencies",
                message="Required dependencies are missing from pyproject.toml.",
                details={
                    "missing_dependencies": ", ".join(missing),
                    "remediation": "Add Beancount and Fava to [project].dependencies before bootstrapping.",
                },
            )
        return DiagnosticCheck(
            name="declared_dependencies",
            status=CheckStatus.PASS,
            error_code=None,
            message="Required dependencies are declared in pyproject.toml.",
            details={"dependencies": ", ".join(REQUIRED_DEPENDENCIES)},
        )

    def _normalize_dependency_name(self, entry: str) -> str | None:
        requirement = entry.split(";", 1)[0].strip()
        if not requirement:
            return None
        name_portion = requirement.split("[", 1)[0].strip()
        match = DEPENDENCY_NAME_PATTERN.match(name_portion)
        if match is None:
            return None
        return match.group(0).lower().replace("_", "-")

    def _build_uv_sync_check(self, sync_result) -> DiagnosticCheck:
        details = {
            "command": "uv sync",
            "stdout": sync_result.stdout,
            "stderr": sync_result.stderr,
        }
        if sync_result.returncode == 0:
            return DiagnosticCheck(
                name="uv_sync",
                status=CheckStatus.PASS,
                error_code=None,
                message="Project environment synced successfully.",
                details=details,
            )

        combined_output = f"{sync_result.stdout}\n{sync_result.stderr}".lower()
        if "bison" in combined_output:
            details["remediation"] = (
                "Beancount appears to be building from source on this machine. Install Bison >= 3.8, "
                "ensure it is first on PATH, then rerun bootstrap."
            )
            return DiagnosticCheck(
                name="uv_sync",
                status=CheckStatus.FAIL,
                error_code="uv_sync_missing_bison",
                message="uv sync failed because the current Beancount install path needs a newer Bison toolchain.",
                details=details,
            )

        details["remediation"] = "Review the uv sync output, fix the reported prerequisite, then rerun bootstrap."
        return DiagnosticCheck(
            name="uv_sync",
            status=CheckStatus.FAIL,
            error_code="uv_sync_failed",
            message="uv sync failed. Review stderr and rerun after addressing the issue.",
            details=details,
        )

    def _run_import_check(self) -> DiagnosticCheck:
        python_path = self.paths.venv_directory / "bin" / "python"
        if not python_path.is_file():
            return DiagnosticCheck(
                name="python_imports",
                status=CheckStatus.FAIL,
                error_code="missing_environment_python",
                message="The repo-local Python executable is missing from the uv-managed environment.",
                details={
                    "expected_path": str(python_path),
                    "remediation": "Run 'auto-bean bootstrap' to create the project environment.",
                },
            )
        command = [
            str(python_path),
            "-c",
            "import auto_bean, beancount, fava",
        ]
        result = self.command_runner.run(command, cwd=self.paths.repo_root)
        if result.returncode != 0:
            return DiagnosticCheck(
                name="python_imports",
                status=CheckStatus.FAIL,
                error_code="python_import_check_failed",
                message="Python package imports failed in the uv-managed environment.",
                details={
                    "command": " ".join(command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "remediation": "Run 'auto-bean bootstrap' to sync dependencies, then rerun readiness.",
                },
            )
        return DiagnosticCheck(
            name="python_imports",
            status=CheckStatus.PASS,
            error_code=None,
            message="auto-bean, Beancount, and Fava import successfully.",
            details={"command": " ".join(command)},
        )

    def _run_entrypoint_check(self) -> DiagnosticCheck:
        entrypoint_path = self.paths.venv_directory / "bin" / "auto-bean"
        if not entrypoint_path.is_file():
            return DiagnosticCheck(
                name="auto_bean_entrypoint",
                status=CheckStatus.FAIL,
                error_code="missing_auto_bean_entrypoint",
                message="The auto-bean entrypoint is missing from the repo-local environment.",
                details={
                    "expected_path": str(entrypoint_path),
                    "remediation": "Run 'auto-bean bootstrap' to install the package into the project environment.",
                },
            )
        command = [str(entrypoint_path), "--help"]
        result = self.command_runner.run(command, cwd=self.paths.repo_root)
        if result.returncode != 0:
            return DiagnosticCheck(
                name="auto_bean_entrypoint",
                status=CheckStatus.FAIL,
                error_code="entrypoint_unavailable",
                message="The auto-bean entrypoint is not runnable through the uv environment.",
                details={
                    "command": " ".join(command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "remediation": "Run 'auto-bean bootstrap' to install the package into the project environment.",
                },
            )
        return DiagnosticCheck(
            name="auto_bean_entrypoint",
            status=CheckStatus.PASS,
            error_code=None,
            message="The auto-bean entrypoint is runnable.",
            details={"command": " ".join(command)},
        )

    def _run_tool_command_check(
        self,
        executable_name: str,
        arguments: list[str],
        name: str,
        tool_name: str,
    ) -> DiagnosticCheck:
        executable_path = self.paths.venv_directory / "bin" / executable_name
        if not executable_path.is_file():
            return DiagnosticCheck(
                name=name,
                status=CheckStatus.FAIL,
                error_code=f"missing_{tool_name}_executable",
                message=f"{tool_name} is missing from the repo-local environment.",
                details={
                    "expected_path": str(executable_path),
                    "remediation": "Run 'auto-bean bootstrap' and confirm the dependency installed correctly.",
                },
            )
        command = [str(executable_path), *arguments]
        result = self.command_runner.run(command, cwd=self.paths.repo_root)
        if result.returncode != 0:
            return DiagnosticCheck(
                name=name,
                status=CheckStatus.FAIL,
                error_code=f"{tool_name}_unavailable",
                message=f"{tool_name} is not runnable through the uv-managed environment.",
                details={
                    "command": " ".join(command),
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "remediation": "Run 'auto-bean bootstrap' and confirm the dependency installed correctly.",
                },
            )
        return DiagnosticCheck(
            name=name,
            status=CheckStatus.PASS,
            error_code=None,
            message=f"{tool_name} is runnable through the uv-managed environment.",
            details={"command": " ".join(command)},
        )

    def _result(
        self,
        *,
        status: str,
        error_code: str | None,
        message: str,
        details: dict[str, str],
        checks: tuple[DiagnosticCheck, ...],
        started: float,
    ) -> WorkflowResult:
        return WorkflowResult(
            status=status,
            error_code=error_code,
            message=message,
            details=details,
            checks=checks,
            duration_seconds=current_time() - started,
        )

def build_setup_service(start: Path | None = None) -> SetupService:
    return SetupService(
        paths=ProjectPaths(start=start),
        platform_probe=PlatformProbe(),
        tool_probe=ToolProbe(),
        command_runner=CommandRunner(),
    )
