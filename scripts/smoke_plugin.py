"""Exercise a packaged install with the actual locked ledger runtime."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

from package_plugin import PLUGIN, package_plugin


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="auto-bean smoke ") as temporary:
        directory = Path(temporary)
        archive = package_plugin(directory / "plugin.zip")
        installed = directory / "installed plugin"
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(installed)
        before = {
            p.relative_to(installed): p.read_bytes()
            for p in installed.rglob("*")
            if p.is_file()
        }
        for path in installed.rglob("*"):
            if path.is_file():
                path.chmod(0o444)
        root = directory / "my ledger"
        launch = ["sh", str(installed / "runtime/launch.sh")]
        env = dict(
            os.environ,
            GIT_AUTHOR_NAME="Plugin Smoke",
            GIT_AUTHOR_EMAIL="smoke@example.test",
            GIT_COMMITTER_NAME="Plugin Smoke",
            GIT_COMMITTER_EMAIL="smoke@example.test",
        )

        def run(*args: str) -> str:
            result = subprocess.run(
                [*launch, *args], cwd=directory, env=env, text=True, capture_output=True
            )
            if result.returncode:
                raise RuntimeError(
                    f"Smoke command {args} failed: {result.stdout}\n{result.stderr}"
                )
            return result.stdout

        outcome = json.loads(run("init", "--workspace", str(root)))
        assert outcome["validated"] and outcome["status"] == "ok", outcome
        command = ("run", "--workspace", str(root))
        run(*command, "bean-check", "ledger.beancount")
        run(
            *command,
            "python",
            "-c",
            "import importlib.util; assert importlib.util.find_spec('docling') is None; assert importlib.util.find_spec('torch') is None",
        )
        run(
            *command,
            "python",
            str(installed / "runtime/validate_state.py"),
            "memory",
            ".auto-bean/memory/category_mappings.json",
        )
        run(
            *command,
            "bean-query",
            "ledger.beancount",
            "SELECT account, sum(position) GROUP BY account;",
        )
        with (root / "ledger.beancount").open("a") as stream:
            stream.write(
                '\n2026-01-01 * "Smoke transaction"\n  Assets:Checking  10 EUR\n  Equity:Opening-Balances\n'
            )
        run(*command, "bean-check", "ledger.beancount")
        answer = run(
            *command,
            "bean-query",
            "ledger.beancount",
            "SELECT account, sum(position) GROUP BY account;",
        )
        assert "10 EUR" in answer, answer
        boundary = root / "period-boundaries.beancount"
        boundary.write_bytes(
            (
                Path(__file__).resolve().parents[1]
                / "tests/fixtures/period-boundaries.beancount"
            ).read_bytes()
        )
        run(*command, "bean-check", boundary.name)
        patterns = (
            installed / "skills/auto-bean-query/references/bean-query-patterns.md"
        ).read_text()
        queries = re.findall(r"```sql\n(.*?)```", patterns, re.DOTALL)
        assert queries
        for query in queries:
            result = run(*command, "bean-query", boundary.name, query)
            if "FROM OPEN ON" in query:
                assert "31 EUR" in result and "1031 EUR" not in result, result
        # No prices are configured in this fixture: a dry run must terminate without a live fetch.
        run(
            *command,
            "bean-price",
            "--dry-run",
            "--date",
            "2026-01-01",
            "ledger.beancount",
        )
        run(*command, "docling", "--help")
        # A small statement exercises a supported import format without PDF model downloads.
        raw = root / "statements/raw/sample.csv"
        raw.write_text(
            "Date,Description,Amount,Currency\n2026-01-01,Smoke deposit,10.00,EUR\n"
        )
        run(
            *command,
            "docling",
            str(raw),
            "--to",
            "json",
            "--output",
            ".auto-bean/tmp/docling-smoke",
        )
        extracted = list((root / ".auto-bean/tmp/docling-smoke").glob("*.json"))
        assert extracted and "Smoke deposit" in extracted[0].read_text()
        # Bind an ephemeral localhost port to avoid colliding with a user's Fava session.
        import socket

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        process = subprocess.Popen(
            [
                *launch,
                *command,
                "fava",
                "ledger.beancount",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=directory,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    details = process.stderr.read().decode() if process.stderr else ""
                    raise RuntimeError(f"Fava exited: {details}")
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/", timeout=1
                    ) as response:
                        assert response.status == 200
                        break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Fava did not serve the ledger")
        finally:
            process.terminate()
            process.wait(timeout=10)
            if process.stderr:
                process.stderr.close()
        after = {
            p.relative_to(installed): p.read_bytes()
            for p in installed.rglob("*")
            if p.is_file()
        }
        assert before == after, "Plugin installation was mutated"
        assert not (root / ".agents").exists()
        assert not (root / "scripts").exists()

        # Exercise reviewed migration using the real runtime, including byte-preserved state.
        legacy = directory / "legacy ledger"
        run("init", "--workspace", str(legacy))
        (legacy / ".auto-bean/workspace.json").unlink()
        old_skill = legacy / ".agents/skills/auto-bean-query/SKILL.md"
        old_skill.parent.mkdir(parents=True)
        old_skill.write_text("Customized legacy query instructions")
        unrelated = legacy / ".agents/skills/personal/SKILL.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("Unrelated skill")
        protected = [
            legacy / "ledger.beancount",
            *(legacy / "beancount").glob("*.beancount"),
            *(legacy / ".auto-bean/memory").rglob("*"),
        ]
        originals = {path: path.read_bytes() for path in protected if path.is_file()}
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=legacy)
        plan = json.loads(run("migrate", "--workspace", str(legacy)))
        result = json.loads(
            run("migrate", "--workspace", str(legacy), "--apply", plan["plan_id"])
        )
        assert result["status"] == "ok"
        assert not old_skill.exists()
        assert unrelated.read_text() == "Unrelated skill"
        assert (
            Path(result["backup"]) / ".agents/skills/auto-bean-query/SKILL.md"
        ).read_text() == "Customized legacy query instructions"
        assert all(path.read_bytes() == data for path, data in originals.items())
        assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=legacy) == head
        assert json.loads(run("migrate", "--workspace", str(legacy)))["changes"] == []
        print(
            f"Packaged {PLUGIN.name}: init, validation, BQL, transaction, CSV extraction, price dry-run, Fava, and legacy migration passed."
        )


if __name__ == "__main__":
    main()
