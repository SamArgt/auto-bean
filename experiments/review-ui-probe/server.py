"""Isolated MCP compatibility probe. It never reads or writes a ledger."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.stdio import stdio_server
from pydantic import AnyUrl

URI = "ui://auto-bean-review-probe/panel"
server: Server[Any] = Server("auto-bean-review-probe", version="0.1.0")
EMPTY = {"type": "object", "properties": {}, "additionalProperties": False}


def state_path() -> Path:
    # No ledger path or arbitrary path is accepted through tool arguments.
    root = Path(os.environ.get("TMPDIR", "/tmp")) / "auto-bean-review-probe"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError("Probe data directory must not be a symlink")
    return root / "synthetic-actions.json"


def state() -> dict[str, Any]:
    path = state_path()
    if path.is_symlink():
        raise ValueError("Probe data file must not be a symlink")
    return json.loads(path.read_text()) if path.exists() else {"actions": []}


@server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="open_review_probe",
            title="Import Review Probe",
            description="Open the synthetic local side-panel compatibility test. No ledger access.",
            inputSchema=EMPTY,
            annotations=types.ToolAnnotations(readOnlyHint=True, openWorldHint=False),
            _meta={
                "ui": {"resourceUri": URI},
                "openai/ui": {"entrypoints": [{"type": "thread"}]},
            },
        ),
        types.Tool(
            name="save_probe_action",
            description="Save an idempotent synthetic button action. No ledger changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action_id": {"type": "string", "pattern": "^[a-zA-Z0-9-]{1,80}$"}
                },
                "required": ["action_id"],
                "additionalProperties": False,
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=False,
            ),
            _meta={"ui": {"visibility": ["app"]}},
        ),
    ]


@server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl(URI), name="Review probe", mimeType="text/html;profile=mcp-app"
        )
    ]


@server.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
async def read_resource(uri: Any) -> list[ReadResourceContents]:
    if str(uri) != URI:
        raise ValueError("Unknown resource")
    return [
        ReadResourceContents(
            content=Path(__file__).with_name("panel.html").read_text(),
            mime_type="text/html;profile=mcp-app",
            meta={
                "openai/ui": {
                    "availableDisplayModes": ["fullscreen"],
                    "preferredDisplayMode": "fullscreen",
                }
            },
        )
    ]


@server.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
    current = state()
    if name == "save_probe_action":
        action = arguments["action_id"]
        if action not in current["actions"]:
            current["actions"].append(action)
            temporary = state_path().with_suffix(".tmp")
            temporary.write_text(json.dumps(current))
            temporary.replace(state_path())
    elif name != "open_review_probe":
        raise ValueError("Unknown tool")
    data = {
        "session_id": "synthetic-probe",
        "statement": "example.csv",
        "status": "account_review",
        **current,
    }
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(data))],
        structuredContent=data,
    )


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
