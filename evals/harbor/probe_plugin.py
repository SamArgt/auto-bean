"""Check installed, enabled plugin skills with the pinned Codex app-server API."""

from __future__ import annotations

import json
import subprocess
import asyncio
from pathlib import Path
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


EXPECTED_MCP_TOOLS = {
    "open_import_review",
    "export_import_review",
    "read_import_session",
    "read_import_statement",
    "list_import_transactions",
    "search_ledger_accounts",
    "update_import_review",
    "approve_import_prices",
    "prepare_import_review_batch",
    "acknowledge_import_review_batch",
}


def check_tool_contract(tools: dict[str, Any]) -> None:
    """Require the exact tool set and keep panel tools app-only."""
    missing = sorted(EXPECTED_MCP_TOOLS - set(tools))
    unexpected = sorted(set(tools) - EXPECTED_MCP_TOOLS)
    if missing or unexpected:
        raise RuntimeError(
            f"MCP tool discovery disagrees with review contract: "
            f"missing={missing}, unexpected={unexpected}"
        )
    for name in sorted(
        EXPECTED_MCP_TOOLS - {"open_import_review", "export_import_review"}
    ):
        if tools[name].get("_meta", {}).get("ui", {}).get("visibility") != ["app"]:
            raise RuntimeError(f"MCP tool visibility must be app-only: {name}")


def check_unbound_result(result: dict[str, Any]) -> None:
    """Check the unbound call contract while allowing extra response metadata."""
    data = result.get("structuredContent")
    if (
        result.get("isError") is not False
        or not isinstance(data, dict)
        or data.get("status") != "ok"
        or data.get("result") != {"binding": None}
        or data.get("changed_files") != []
        or data.get("file_sha256") != {}
    ):
        raise RuntimeError(
            "Harmless unbound structured call failed: expected an ok response, "
            "null binding, and an empty change receipt."
        )


async def probe_mcp(plugin: Path) -> None:
    """Exercise the declared stdio transport without creating a ledger workspace."""
    config = json.loads((plugin / "mcp.json").read_text())["mcpServers"][
        "import-review"
    ]
    if config["type"] != "stdio":
        raise RuntimeError("Import review must use local stdio")
    args = [value.replace("${PLUGIN_ROOT}", str(plugin)) for value in config["args"]]
    process = await asyncio.create_subprocess_exec(
        config["command"],
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=None,
        cwd="/tmp",
        limit=8 * 1024 * 1024,
    )
    assert process.stdin and process.stdout

    async def request(
        identifier: int, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        assert process.stdin and process.stdout
        process.stdin.write(
            (
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": identifier,
                        "method": method,
                        "params": params,
                    }
                )
                + "\n"
            ).encode()
        )
        await process.stdin.drain()
        while line := await process.stdout.readline():
            response = json.loads(line)
            if response.get("id") == identifier:
                if "error" in response:
                    raise RuntimeError(f"MCP discovery failed: {response['error']}")
                return dict(response["result"])
        raise RuntimeError("MCP server exited before responding")

    try:
        await request(
            1,
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "harbor-discovery", "version": "1.0"},
            },
        )
        process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        await process.stdin.drain()
        listing = await request(2, "tools/list", {})
        tools = {item["name"]: item for item in listing["tools"]}
        check_tool_contract(tools)
        resources = await request(
            3,
            "resources/read",
            {"uri": tools["open_import_review"]["_meta"]["ui"]["resourceUri"]},
        )
        resource = resources["contents"][0]
        if (
            resource["mimeType"] != "text/html;profile=mcp-app"
            or "Import review" not in resource["text"]
        ):
            raise RuntimeError("Bundled MCP App resource missing")
        result = await request(
            4, "tools/call", {"name": "open_import_review", "arguments": {}}
        )
        check_unbound_result(result)
        print(
            "Local MCP tools, App resource and structured call passed; rendering is tested separately."
        )
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except TimeoutError:
                process.kill()
                await process.wait()


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
        if "import-review" not in plugin["mcpServers"]:
            raise RuntimeError("Import review MCP registration missing")
        print("Auto Bean installed and enabled; all nine skills discovered.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    asyncio.run(
        asyncio.wait_for(
            probe_mcp(Path("/opt/auto-bean-marketplace/plugins/auto-bean")), 90
        )
    )


if __name__ == "__main__":
    probe()
