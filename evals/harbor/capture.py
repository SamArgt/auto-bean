"""Collect runtime checks and a review checkpoint outside the ledger workspace."""

from __future__ import annotations

import argparse
import html
import json
import hashlib
import subprocess
import sys
import tomllib
from pathlib import Path
from datetime import datetime, timezone

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
            "supported_schema_versions": {
                "parsed": [1, 2],
                "session": [1],
                "status": [1],
            },
            "frontend": json.loads((plugin / "ui/build.json").read_text())
            if (plugin / "ui/build.json").is_file()
            else None,
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


def checkpoint(root: Path) -> dict[str, object]:
    """Capture durable proposal data; the separate verifier independently checks it."""
    import hashlib

    sessions = list((root / ".auto-bean/import-sessions").glob("*.json"))
    if len(sessions) != 1:
        raise ValueError("Expected exactly one import session for review capture")
    session = json.loads(sessions[0].read_text())
    documents = {
        doc["source_file"]: doc
        for group in session["groups"]
        for doc in json.loads((root / group["parsed_group"]).read_text())["statements"]
    }
    baseline = {
        p.relative_to(root).as_posix(): p.read_text()
        for p in root.rglob("*.beancount")
        if ".auto-bean" not in p.relative_to(root).parts
    }
    hashes = {
        name: hashlib.sha256(content.encode()).hexdigest()
        for name, content in baseline.items()
    }

    # Capture evidence only. The immutable verifier computes its own expectations.
    def material_hash(document: dict[str, object]) -> str:
        # Capture the review projection; independent verifier recomputes it.
        value = {k: v for k, v in document.items() if k != "review"}
        review = document["review"]
        assert isinstance(review, dict)
        value["review"] = {
            "processing": {
                k: v
                for k, v in review["processing"].items()
                if k in {"needs_input", "suggestions", "answer"}
            }
        }
        return hashlib.sha256(
            (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        ).hexdigest()

    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session["session_id"],
        "session": session,
        "documents": documents,
        "review_digests": {raw: material_hash(doc) for raw, doc in documents.items()},
        "financial_hashes": hashes,
        "baseline_contents": baseline,
        "status": (root / "statements/import-status.yml").read_text(),
    }


def write_review_html(root: Path, output: Path, plugin: Path | None = None) -> None:
    """Save derived review evidence; export failures remain visible, never passes."""
    try:
        sessions = list((root / ".auto-bean/import-sessions").glob("*.json"))
        if len(sessions) != 1:
            raise ValueError(
                "Exactly one import session is needed for a review export."
            )
        session_id = sessions[0].stem
        if plugin is None:
            # The separate verifier already runs in its immutable Python runtime.
            from auto_bean.review_export import render_review_html

            rendered = render_review_html(root, session_id)
        else:
            # Isolated Python excludes cwd and PYTHONPATH. Import only the actual
            # installed plugin, never an auto_bean package in the submitted ledger.
            result = subprocess.run(
                [
                    "sh",
                    str(plugin / "runtime/launch.sh"),
                    "run",
                    "--workspace",
                    str(root),
                    "python",
                    "-I",
                    "-c",
                    "import sys; from pathlib import Path; "
                    "sys.path.insert(0, sys.argv[1]); "
                    "from auto_bean.review_export import render_review_html; "
                    "print(render_review_html(Path(sys.argv[2]), sys.argv[3]))",
                    str(plugin / "runtime"),
                    str(root),
                    session_id,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode:
                raise RuntimeError(
                    result.stderr.strip()[:2000] or "Review export failed."
                )
            rendered = result.stdout
            if not rendered.strip():
                raise ValueError("The review exporter returned an empty document.")
    except Exception as exc:
        rendered = (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Auto Bean — Review unavailable</title><body>"
            "<h1>Import review unavailable</h1>"
            "<p>This run did not produce a readable import review. "
            "This artifact does not indicate a successful import.</p><pre>"
            + html.escape(str(exc))
            + "</pre></body></html>\n"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered)


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
    if phase != "init":
        write_review_html(root, evidence / "review.html", plugin)
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
    if (
        phase in {"review", "correct"}
        and (root / "statements/raw/checking.csv").is_file()
    ):
        write_json(evidence / "review.json", checkpoint(root))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=(
            "metadata",
            "init",
            "review",
            "correct",
            "approve",
            "needs-input",
            "stale",
        ),
        required=True,
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
