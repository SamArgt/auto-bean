"""Preserve Harbor's Codex execution while installing the actual local plugin."""

from __future__ import annotations

from typing import Any
import shlex
from pathlib import Path

from harbor.agents.installed.codex import Codex
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

CODEX_VERSION = "0.163.0"


class AutoBeanCodex(Codex):  # type: ignore[misc]
    """Harbor removes CODEX_HOME after every turn, including between steps."""

    @staticmethod
    def name() -> str:
        return "auto-bean-codex"

    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        # Harbor 0.24 invokes each step's setup.sh before run/resume, but does
        # not expose StepConfig on AgentContext. Capture that native setup's
        # explicit identity before the agent runs; never infer it from resume.
        step = await environment.exec(
            "cat /opt/eval-evidence/step-name 2>/dev/null || printf init"
        )
        phase = step.stdout.strip()
        if phase not in {
            "init",
            "review",
            "correct",
            "approve",
            "needs-input",
            "stale",
        }:
            raise ValueError(f"Unknown Harbor step identity: {phase}")
        await super().run(instruction, environment, context)
        await self.exec_as_agent(
            environment,
            command=(
                "uv run --no-project --python 3.13 /opt/evals/harbor/capture.py "
                f"--phase {phase} --logs {shlex.quote(self.environment_logs_dir.as_posix())}"
            ),
            timeout_sec=150,
        )
        if phase != "init":
            exports = Path(self.logs_dir).parent / "review-exports"
            exports.mkdir(parents=True, exist_ok=True)
            await environment.download_file(
                "/opt/eval-evidence/review.html", exports / f"{phase}.html"
            )
        checkpoint_dir = Path(self.logs_dir).parent / "review-checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        if phase in {"review", "correct"}:
            destination = checkpoint_dir / f"{phase}.json"
            if destination.exists():
                raise RuntimeError(
                    "Refusing to replace an earlier host review checkpoint"
                )
            await environment.download_file(
                "/opt/eval-evidence/review.json", destination
            )
            self._review_checkpoint = destination
        elif hasattr(self, "_review_checkpoint"):
            # Agent-writable copies cannot redefine the preceding review. The
            # host copy is explicitly transferred for the separate verifier.
            await environment.upload_file(
                self._review_checkpoint, "/opt/eval-evidence/review.json"
            )

    async def _upload_effective_config(
        self,
        environment: BaseEnvironment,
        config: dict[str, Any],
        remote_path: str,
    ) -> None:
        await super()._upload_effective_config(environment, config, remote_path)
        # Install after Harbor uploads its effective config, on every turn. Local
        # plugin installation requires no model request or host configuration.
        await self.exec_as_agent(
            environment,
            command=(
                "set -euo pipefail; "
                "codex plugin marketplace add /opt/auto-bean-marketplace >/dev/null; "
                "codex plugin add auto-bean@auto-bean --json >/dev/null; "
                "uv run --no-project --python 3.13 /opt/evals/harbor/probe_plugin.py"
            ),
            env={"CODEX_HOME": self._REMOTE_CODEX_HOME.as_posix()},
            timeout_sec=90,
        )
