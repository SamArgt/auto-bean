"""Check installed, enabled plugin skills with the pinned Codex app-server API."""

from __future__ import annotations

import json
import subprocess
from typing import Any

EXPECTED = {
    "auto-bean-init",
    "auto-bean-import",
    "auto-bean-process",
    "auto-bean-categorize",
    "auto-bean-query",
    "auto-bean-write",
    "auto-bean-prices",
    "auto-bean-memory",
    "auto-bean-migrate",
}


def probe() -> None:
    process = subprocess.Popen(
        ["codex", "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert process.stdin and process.stdout

    def send(value: dict[str, Any]) -> None:
        assert process.stdin
        process.stdin.write(json.dumps(value) + "\n")
        process.stdin.flush()

    def receive(identifier: int) -> dict[str, Any]:
        assert process.stdout
        for line in process.stdout:
            response = json.loads(line)
            if response.get("id") == identifier:
                if "error" in response:
                    raise RuntimeError(
                        f"Codex plugin discovery failed: {response['error']}"
                    )
                return dict(response["result"])
        raise RuntimeError("Codex app-server exited before discovery")

    try:
        send(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "auto-bean-harbor", "version": "1.0.0"},
                    "capabilities": {"experimentalApi": True},
                },
            }
        )
        receive(1)
        send({"method": "initialized"})
        send(
            {
                "id": 2,
                "method": "plugin/read",
                "params": {
                    "marketplacePath": "/opt/auto-bean-marketplace/.agents/plugins/marketplace.json",
                    "pluginName": "auto-bean",
                },
            }
        )
        plugin = receive(2)["plugin"]
        summary = plugin["summary"]
        if not summary["installed"] or not summary["enabled"]:
            raise RuntimeError("Auto Bean is not installed and enabled")
        names = {
            skill["name"].split(":")[-1]
            for skill in plugin["skills"]
            if skill["enabled"]
        }
        if names != EXPECTED:
            raise RuntimeError("Installed Auto Bean skill set disagrees with bundle")
        print("Auto Bean installed and enabled; all nine skills discovered.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    probe()
