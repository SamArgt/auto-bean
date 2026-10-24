"""Exercise the build probe against the current MCP response contract."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

import pytest

from auto_bean.common import PLUGIN
from evals.harbor.probe_plugin import (
    EXPECTED_MCP_TOOLS,
    check_tool_contract,
    check_unbound_result,
    probe_mcp,
)


@pytest.mark.parametrize(
    "defect", [None, "missing", "unexpected", "visible", "no_meta"]
)
@pytest.mark.parametrize(
    "name", ["prepare_import_review_batch", "acknowledge_import_review_batch"]
)
def test_batch_tool_discovery_contract(name: str, defect: str | None) -> None:
    tools: dict[str, Any] = {
        key: {"_meta": {"ui": {"visibility": ["app"]}}} for key in EXPECTED_MCP_TOOLS
    }
    if defect == "missing":
        del tools[name]
    elif defect == "unexpected":
        tools["unknown_tool"] = {}
    elif defect == "visible":
        tools[name]["_meta"]["ui"]["visibility"] = ["app", "model"]
    elif defect == "no_meta":
        tools[name] = {}
    if defect is None:
        check_tool_contract(tools)
    else:
        with pytest.raises(RuntimeError, match="MCP tool"):
            check_tool_contract(tools)


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "extra_metadata",
        "error",
        "binding",
        "changed",
        "missing_receipt",
        "missing_hashes",
        "missing_content",
    ],
)
def test_build_probe_response_contract(defect: str | None) -> None:
    data: dict[str, Any] = {
        "status": "ok",
        "result": {"binding": None},
        "changed_files": [],
        "file_sha256": {},
    }
    response: dict[str, Any] = {"isError": False, "structuredContent": data}
    if defect == "extra_metadata":
        data["additional_metadata"] = {"version": 1}
    elif defect == "error":
        response["isError"] = True
    elif defect == "binding":
        data["result"] = {"binding": {"workspace": "/unexpected"}}
    elif defect == "changed":
        data["changed_files"] = ["ledger.beancount"]
    elif defect == "missing_receipt":
        del data["changed_files"]
    elif defect == "missing_hashes":
        del data["file_sha256"]
    elif defect == "missing_content":
        del response["structuredContent"]
    if defect in {None, "extra_metadata"}:
        check_unbound_result(response)
    else:
        with pytest.raises(RuntimeError, match="empty change receipt"):
            check_unbound_result(response)


def test_build_probe_accepts_real_mcp_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Use the same raw JSON-RPC probe as Docker, with the development interpreter.
    (tmp_path / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "import-review": {
                        "type": "stdio",
                        "command": sys.executable,
                        "args": ["-m", "auto_bean.server"],
                    }
                }
            }
        )
    )
    monkeypatch.setenv("PYTHONPATH", str(PLUGIN / "runtime"))
    asyncio.run(asyncio.wait_for(probe_mcp(tmp_path), timeout=30))
    assert "structured call passed" in capsys.readouterr().out
