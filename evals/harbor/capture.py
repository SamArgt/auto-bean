"""Collect runtime checks and a review checkpoint outside the ledger workspace."""

from __future__ import annotations

import argparse
import json
import hashlib
import subprocess
import sys
import tomllib
from pathlib import Path

from evals.harbor.fixtures import sha256, write_json


def metadata(plugin: Path, evidence: Path) -> None:
    """Record the actual checkout copied into the image, without host secrets."""
    digest = hashlib.sha256()
    for path in sorted(plugin.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(path.relative_to(plugin).as_posix().encode() + b"\0")
            digest.update(path.read_bytes())
    lock = plugin / "runtime/uv.lock"
    packages = tomllib.loads(lock.read_text())["package"]
    write_json(
        evidence / "build.json",
        {
            "plugin_tree_sha256": digest.hexdigest(),
            "runtime_lock_sha256": sha256(lock),
            "runtime_dependencies": [
                {"name": package["name"], "version": package["version"]}
                for package in packages
                if "version" in package
            ],
            "python_version": sys.version.split()[0],
            "codex_version": subprocess.check_output(
                ["codex", "--version"], text=True
            ).strip(),
            "pdf_model_revisions": sorted(
                str(path.relative_to(Path.home() / ".cache/huggingface/hub"))
                for path in (Path.home() / ".cache/huggingface/hub").glob(
                    "models--*/snapshots/*"
                )
                if path.is_dir()
            ),
        },
    )


def capture(
    root: Path, plugin: Path, evidence: Path, phase: str, logs: Path | None = None
) -> None:
    evidence.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "sh",
            str(plugin / "runtime/launch.sh"),
            "run",
            "--workspace",
            str(root),
            "bean-check",
            "ledger.beancount",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    write_json(
        evidence / "runtime.json",
        {
            "validated": result.returncode == 0,
            "runtime_present": any(
                (root / ".auto-bean/runtime").glob("*/.venv/bin/bean-check")
            ),
        },
    )
    if logs is not None:
        messages = []
        output = logs / "codex.txt"
        if output.is_file():
            for line in output.read_text().splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                item = event.get("item", {})
                if (
                    event.get("type") == "item.completed"
                    and item.get("type") == "agent_message"
                ):
                    messages.append(item.get("text", ""))
        (evidence / "last-response.txt").write_text(messages[-1] if messages else "")
    if phase == "initial" and (root / "statements/raw/checking.csv").is_file():
        write_json(
            evidence / "review.json",
            {
                "financial_hashes": {
                    path.relative_to(root).as_posix(): sha256(path)
                    for path in sorted(root.rglob("*.beancount"))
                    if ".auto-bean" not in path.relative_to(root).parts
                },
                "status": (root / "statements/import-status.yml").read_text(),
            },
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", choices=("metadata", "initial", "approve"), required=True
    )
    parser.add_argument("--logs", type=Path)
    args = parser.parse_args()
    plugin = Path("/opt/auto-bean-marketplace/plugins/auto-bean")
    evidence = Path("/opt/eval-evidence")
    if args.phase == "metadata":
        metadata(plugin, evidence)
        raise SystemExit(0)
    capture(
        Path("/app/ledger"),
        plugin,
        evidence,
        args.phase,
        args.logs,
    )
