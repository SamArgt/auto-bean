"""Real stdio transport checks; no renderer claims or HTTP server."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from jsonschema import Draft202012Validator
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl

from auto_bean.common import PLUGIN, digest
from auto_bean.review import ReviewFiles, etag
from auto_bean.server import CONTRACTS, dispatch, output_schema, validate
from test_review import PARSED, SOURCE, complete, review_store, save

__all__ = ["review_store"]


def test_stdio_discovery_without_workspace_and_ui_resource(tmp_path: Path) -> None:
    async def scenario() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "auto_bean.server"],
            cwd=str(tmp_path),
            env={**os.environ, "PYTHONPATH": str(PLUGIN / "runtime")},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listing = await session.list_tools()
                names = {tool.name for tool in listing.tools}
                for tool in listing.tools:
                    for kind, schema in (
                        ("input", tool.inputSchema),
                        ("output", tool.outputSchema),
                    ):
                        assert schema is not None
                        Draft202012Validator.check_schema(schema)
                        assert schema["$id"].endswith(f"/{tool.name}/{kind}")
                assert {
                    "open_import_review",
                    "read_import_session",
                    "update_import_review",
                    "list_import_transactions",
                    "export_import_review",
                } <= names
                exporter = next(
                    t for t in listing.tools if t.name == "export_import_review"
                )
                assert exporter.annotations
                assert exporter.annotations.readOnlyHint is False
                assert not exporter.meta or exporter.meta.get("ui", {}).get(
                    "visibility"
                ) != ["app"]
                assert "create_import_session" not in names
                for tool in listing.tools:
                    if tool.name not in {"open_import_review", "export_import_review"}:
                        assert tool.meta and tool.meta["ui"]["visibility"] == ["app"]
                action = next(
                    t for t in listing.tools if t.name == "update_import_review"
                )
                assert action.meta and action.meta["ui"]["visibility"] == ["app"]
                result = await session.call_tool("open_import_review", {})
                assert result.structuredContent == {
                    "status": "ok",
                    "result": {"binding": None},
                    "changed_files": [],
                    "file_sha256": {},
                }
                opener = next(
                    t for t in listing.tools if t.name == "open_import_review"
                )
                assert opener.meta
                uri = opener.meta["ui"]["resourceUri"]
                assert uri.startswith("ui://auto-bean/import-review/")
                resource = await session.read_resource(AnyUrl(uri))
                assert resource.contents[0].mimeType == "text/html;profile=mcp-app"
                assert "Import review" in resource.contents[0].text  # type: ignore[union-attr]
                for arguments in (
                    {"extra": True},
                    {"workspace": ""},
                    {"workspace": str(tmp_path)},
                    {"workspace": " ", "session_id": "test"},
                ):
                    bad = await session.call_tool("open_import_review", arguments)
                    assert bad.isError
                bad = await session.call_tool(
                    "read_import_statement",
                    {
                        "workspace": str(tmp_path),
                        "session_id": "test",
                        "source_file": "",
                    },
                )
                assert bad.isError
        assert not (tmp_path / "ledger.beancount").exists()

    asyncio.run(scenario())


def test_stdio_exports_valid_session_without_changing_ledger(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    complete(store)
    before = {
        str(path.relative_to(store.root)): path.read_bytes()
        for path in store.root.rglob("*")
        if path.is_file()
    }

    async def scenario() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "auto_bean.server"],
            cwd=str(store.root),
            env={**os.environ, "PYTHONPATH": str(PLUGIN / "runtime")},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listing = await session.list_tools()
                exporter = next(
                    tool
                    for tool in listing.tools
                    if tool.name == "export_import_review"
                )
                response = await session.call_tool(
                    exporter.name,
                    {"workspace": str(store.root), "session_id": store.session_id},
                )
                assert not response.isError
                assert response.structuredContent is not None
                assert exporter.outputSchema is not None
                Draft202012Validator(exporter.outputSchema).validate(
                    response.structuredContent
                )
                result = response.structuredContent["result"]
                assert set(result) == {"path", "filename", "sha256", "exported_at"}
                path = Path(result["path"])
                assert path.is_absolute()
                assert path.parent == store.root / ".auto-bean/exports"
                assert result["filename"] == path.name
                content = path.read_bytes()
                assert digest(content) == result["sha256"]
                assert result["exported_at"] in content.decode()
                assert b"Market" in content
                assert b"test-session" in content

    asyncio.run(scenario())
    assert all(
        (store.root / path).read_bytes() == value for path, value in before.items()
    )


def test_unified_tool_rows_and_pending_input_filter(review_store: ReviewFiles) -> None:
    store = review_store
    complete(store)
    args = {
        "workspace": str(store.root),
        "session_id": store.session_id,
        "source_file": SOURCE,
    }
    detail = dispatch("read_import_statement", args)
    assert "accounts" not in detail and "questions" not in detail
    assert (
        detail["statement_metadata"]["accounts"][0]["review"]["ledger_account"]
        == "Assets:Checking"
    )
    page = dispatch("list_import_transactions", args)
    validate(
        output_schema(CONTRACTS["list_import_transactions"][1]),
        {"status": "ok", "result": page},
    )
    assert page["etag"] == detail["etag"]
    assert page["rows"][0]["record_id"] == "row-1"
    assert page["rows"][0]["review"]["postings"]
    assert "record" not in page["rows"][0] and "decision" not in page["rows"][0]
    document = store.statement(SOURCE)
    document["extracted_records"][0].pop("review")
    save(store, PARSED, document)
    assert "review" not in dispatch("list_import_transactions", args)["rows"][0]
    assert (
        dispatch("list_import_transactions", {**args, "needs_input": True})["total"]
        == 0
    )


def test_stdio_saves_inline_correction_and_rejects_stale_retry(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    document = complete(store)
    ledger_before = (store.root / "ledger.beancount").read_bytes()

    async def scenario() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "auto_bean.server"],
            cwd=str(store.root),
            env={**os.environ, "PYTHONPATH": str(PLUGIN / "runtime")},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                args = {
                    "workspace": str(store.root),
                    "session_id": store.session_id,
                    "source_file": SOURCE,
                    "update": {
                        "kind": "mapping",
                        "subject_id": "checking",
                        "value": "Assets:Checking",
                        "expected_etag": etag(document),
                    },
                }
                result = await client.call_tool("update_import_review", args)
                assert not result.isError
                assert result.structuredContent
                receipt = result.structuredContent["result"]
                changed = result.structuredContent["changed_files"]
                assert changed == [PARSED]
                assert result.structuredContent["file_sha256"] == {
                    PARSED: digest((store.root / PARSED).read_bytes())
                }
                assert set(receipt) == {"source_file", "etag", "review_digest"}
                assert receipt["etag"] == etag(store.statement(SOURCE))
                stale = await client.call_tool("update_import_review", args)
                assert stale.isError
                assert stale.structuredContent
                assert stale.structuredContent["error_code"] == "edit_conflict"
                detail = await client.call_tool(
                    "read_import_statement",
                    {
                        "workspace": str(store.root),
                        "session_id": store.session_id,
                        "source_file": SOURCE,
                    },
                )
                assert not detail.isError
                assert detail.structuredContent
                value = detail.structuredContent["result"]
                assert (
                    value["statement_metadata"]["accounts"][0]["review"][
                        "ledger_account"
                    ]
                    == "Assets:Checking"
                )
                assert (
                    value["statement_metadata"]["accounts"][0]["review"]["state"]
                    == "needs_input"
                )
                assert value["approval"] is None and value["validation"] is None
                assert "actions" not in value

    asyncio.run(scenario())
    assert (store.root / "ledger.beancount").read_bytes() == ledger_before


def test_price_approval_uses_current_run_and_does_not_write_ledger(
    review_store: ReviewFiles,
) -> None:
    store = review_store
    args = {"workspace": str(store.root), "session_id": store.session_id}
    run = {
        "run_id": "prices",
        "requested_date": "2026-01-31",
        "state": "complete",
        "required_commodities": ["STOCK"],
        "coverage": ["STOCK"],
        "preflight": "passed",
        "preflight_job_count": 1,
        "execution": {
            "state": "complete",
            "exit_code": 0,
            "duration_seconds": 0,
            "stderr_summary": "",
        },
        "jobs": [
            {
                "commodity": "STOCK",
                "source": "fixture",
                "requested_date": "2026-01-31",
                "quote_date": "2026-01-31",
                "outcome": "emitted",
                "directive": "2026-01-31 price STOCK 20 EUR",
            }
        ],
        "detail": "Synthetic result",
    }
    session = store.read(store.session_path)
    session["price_runs"] = [run]
    (store.root / store.session_path).write_text(json.dumps(session))
    overview = dispatch("read_import_session", args)
    review_digest = overview["price_runs"][0]["review_digest"]
    assert "review_digest" not in store.read(store.session_path)["price_runs"][0]
    before = (store.root / "ledger.beancount").read_bytes()
    receipt = dispatch(
        "approve_import_prices",
        {
            **args,
            "run_id": "prices",
            "expected_etag": overview["etag"],
            "review_digest": review_digest,
        },
    )
    validate(
        output_schema(CONTRACTS["approve_import_prices"][1]),
        {"status": "ok", "result": receipt},
    )
    assert receipt == {
        "run_id": "prices",
        "etag": etag(store.read(store.session_path)),
        "review_digest": review_digest,
    }
    current = store.read(store.session_path)["price_runs"][0]
    assert current["approval"]["digest"] == review_digest
    assert current["approval"]["origin"] == "panel"
    assert (store.root / "ledger.beancount").read_bytes() == before


def test_direct_artifact_edit_invalidates_panel_snapshot(
    review_store: ReviewFiles,
) -> None:
    from auto_bean.common import WorkflowError
    import pytest

    store = review_store
    complete(store)
    args = {
        "workspace": str(store.root),
        "session_id": store.session_id,
        "source_file": SOURCE,
    }
    detail = dispatch("read_import_statement", args)
    document = store.statement(SOURCE)
    assert "revision" not in document
    document["review"]["processing"]["warnings"].append(
        "Agent added extraction context"
    )
    save(store, PARSED, document)
    with pytest.raises(WorkflowError, match="changed"):
        dispatch(
            "update_import_review",
            {
                **args,
                "update": {
                    "kind": "mapping",
                    "subject_id": "checking",
                    "value": "Assets:Checking",
                    "expected_etag": detail["etag"],
                },
            },
        )
    assert store.statement(SOURCE) == document
    current = dispatch("read_import_statement", args)
    assert current["etag"] != detail["etag"]
    assert dispatch("list_import_transactions", args)["etag"] == current["etag"]


def test_session_overview_preserves_group_membership(review_store: ReviewFiles) -> None:
    result = dispatch(
        "read_import_session",
        {"workspace": str(review_store.root), "session_id": review_store.session_id},
    )
    assert result["groups"][0]["current_status"] == "raw_ready"
    assert result["groups"][0]["source_files"] == [SOURCE]
    Draft202012Validator(CONTRACTS["read_import_session"][1]).validate(result)
