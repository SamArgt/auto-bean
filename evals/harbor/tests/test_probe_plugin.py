"""Exercise the build probe against the current MCP response contract."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

import pytest

from auto_bean.common import PLUGIN
from evals.harbor.probe_plugin import check_unbound_result, probe_mcp


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
