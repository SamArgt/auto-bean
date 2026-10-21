"""Preserve Harbor's Codex execution while installing the actual local plugin."""

from __future__ import annotations

from typing import Any
import shlex

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
        await super().run(instruction, environment, context)
        phase = "approve" if self._resume else "initial"
        await self.exec_as_agent(
            environment,
            command=(
                "uv run --no-project --python 3.13 /opt/evals/harbor/capture.py "
                f"--phase {phase} --logs {shlex.quote(self.environment_logs_dir.as_posix())}"
            ),
            timeout_sec=150,
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
