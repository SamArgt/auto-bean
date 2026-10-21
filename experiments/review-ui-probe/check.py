"""Exercise the probe over real stdio; this is not a desktop rendering test."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="auto-bean-probe-check-") as scratch:
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(Path(__file__).with_name("server.py"))],
            env={**os.environ, "TMPDIR": scratch},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                assert {tool.name for tool in tools} == {
                    "open_review_probe",
                    "save_probe_action",
                }
                panel = await session.read_resource(
                    AnyUrl("ui://auto-bean-review-probe/panel")
                )
                assert panel.contents[0].mimeType == "text/html;profile=mcp-app"
                result = await session.call_tool("open_review_probe", {})
                assert not result.isError
                assert result.structuredContent is not None
                assert result.structuredContent["status"] == "account_review"
                for _ in range(2):
                    saved = await session.call_tool(
                        "save_probe_action", {"action_id": "synthetic-1"}
                    )
                    assert not saved.isError
                    assert saved.structuredContent is not None
                    assert saved.structuredContent["actions"] == ["synthetic-1"]
                invalid = await session.call_tool(
                    "save_probe_action", {"action_id": "../escape"}
                )
                assert invalid.isError
        # Persistence is verified after the MCP server exits.
        data = Path(scratch) / "auto-bean-review-probe/synthetic-actions.json"
        assert data.read_text() == '{"actions": ["synthetic-1"]}'
        print(
            "PASS: stdio discovery, UI resource, structured read, durable idempotent action, input rejection."
        )
        print(
            "NOT TESTED: desktop rendering, bridge tool calls, same-conversation continuation."
        )


if __name__ == "__main__":
    asyncio.run(main())
