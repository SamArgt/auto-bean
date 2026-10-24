"""Local stdio MCP Apps review surface. No HTTP listener or telemetry."""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.stdio import stdio_server
from pydantic import AnyUrl

from auto_bean.common import (
    PLUGIN,
    WorkflowError,
    change_report,
    checked_path,
    record_changes,
)
from auto_bean.review import (
    ReviewFiles,
    account_decisions,
    etag,
    material,
    price_material,
    transaction_decisions,
)
from auto_bean.review_export import validation_current
from auto_bean.validation import (
    session_members,
    status_members,
    session_status,
    FORMATS,
    invalid,
    load_state,
    validate_state,
)

UI_BUILD = json.loads((PLUGIN / "ui/build.json").read_text())
# Hosts cache UI resources by URI. New bundles must have a new resource identity.
URI = f"ui://auto-bean/import-review/{UI_BUILD['bundle_sha256']}.html"
server: Server[Any] = Server("auto-bean-import-review", version="0.2.0")
S: dict[str, Any] = {"type": "string"}
HASH = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
N: dict[str, Any] = {"type": "integer", "minimum": 0}


def obj(
    properties: dict[str, Any], required: list[str] | None = None
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


def array(item: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": item}


def nullable(item: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [item, {"type": "null"}]}


PARSED = json.loads((PLUGIN / "references/schemas/parsed-v2.schema.json").read_text())
SESSION = json.loads((PLUGIN / "references/schemas/session.schema.json").read_text())
R = PARSED["properties"]["review"]["properties"]
NONEMPTY = {"type": "string", "minLength": 1, "pattern": r"\S"}
ID = SESSION["properties"]["session_id"]
BIND = {"workspace": NONEMPTY, "session_id": ID}
SOURCE = {**BIND, "source_file": NONEMPTY}
UPDATE = obj(
    {
        "kind": {"enum": ["answer", "mapping", "postings", "approve", "reject"]},
        "subject_id": ID,
        "subject_kind": {"enum": ["statement", "account", "transaction"]},
        "value": {
            "oneOf": [
                NONEMPTY,
                array(
                    PARSED["properties"]["extracted_records"]["items"]["properties"][
                        "review"
                    ]["properties"]["postings"]["items"]
                ),
            ]
        },
        "expected_etag": HASH,
        "review_digest": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    },
    ["kind", "subject_id", "expected_etag"],
)
UPDATE["allOf"] = [
    {
        "if": {"properties": {"kind": {"enum": ["approve", "reject"]}}},
        "then": {"required": ["review_digest"]},
    },
    {
        "if": {"properties": {"kind": {"enum": ["answer", "mapping", "postings"]}}},
        "then": {"required": ["value"]},
    },
    {
        "if": {"properties": {"kind": {"enum": ["answer", "mapping"]}}},
        "then": {"properties": {"value": NONEMPTY}},
    },
    {
        "if": {"properties": {"kind": {"const": "postings"}}},
        "then": {"properties": {"value": {"type": "array", "minItems": 2}}},
    },
    {
        "if": {"properties": {"kind": {"const": "answer"}}},
        "then": {"required": ["subject_kind"]},
    },
]
SAVED = obj({"source_file": S, "etag": HASH, "review_digest": S})
SUMMARY = obj(
    {
        "source_file": S,
        "parsed_group": S,
        "group_id": ID,
        "status": S,
        "updated_at": nullable(S),
        "etag": nullable(HASH),
        "extraction_state": nullable(S),
        "needs_input": N,
        "error": nullable(S),
    }
)
DETAIL = obj(
    {
        "source_file": S,
        "etag": HASH,
        "extraction_state": S,
        "statement_metadata": PARSED["properties"]["statement_metadata"],
        "processing": R["processing"],
        "review_digest": S,
        "approval": nullable(R["approval"]),
        "validation": nullable(R["validation"]),
        "validation_current": nullable({"type": "boolean"}),
    }
)
PAGE = obj(
    {
        "etag": HASH,
        "total": N,
        "offset": N,
        "rows": array(PARSED["properties"]["extracted_records"]["items"]),
    }
)
PRICE_VIEW = copy.deepcopy(SESSION["properties"]["price_runs"]["items"])
PRICE_VIEW["properties"]["review_digest"] = S
PRICE_VIEW["properties"]["validation_current"] = nullable({"type": "boolean"})
PRICE_VIEW["required"].extend(["review_digest", "validation_current"])
GROUP_VIEW = copy.deepcopy(SESSION["properties"]["groups"]["items"])
GROUP_VIEW["properties"].update({"current_status": S, "updated_at": nullable(S)})
GROUP_VIEW["required"].extend(["current_status", "updated_at"])
BATCH = obj(
    {
        "pending_count": N,
        "pending_token": HASH,
        "token": HASH,
        "blockers": array(S),
        "ready": {"type": "boolean"},
        "subjects": array(S),
    }
)
OVERVIEW = obj(
    {
        **BIND,
        "etag": HASH,
        "statements": array(SUMMARY),
        "groups": array(GROUP_VIEW),
        "price_runs": array(PRICE_VIEW),
        "review_batch": BATCH,
    }
)
CONTRACTS = {
    "open_import_review": (obj(BIND, []), obj({"binding": nullable(obj(BIND))})),
    "export_import_review": (
        obj(BIND),
        obj(
            {
                "path": NONEMPTY,
                "filename": NONEMPTY,
                "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "exported_at": {"type": "string", "format": "date-time"},
            }
        ),
    ),
    "read_import_session": (obj(BIND), OVERVIEW),
    "prepare_import_review_batch": (obj({**BIND, "token": HASH}), BATCH),
    "acknowledge_import_review_batch": (obj({**BIND, "pending_token": HASH}), BATCH),
    "read_import_statement": (obj(SOURCE), DETAIL),
    "list_import_transactions": (
        obj(
            {
                **SOURCE,
                "offset": N,
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "account_id": ID,
                "needs_input": {"type": "boolean"},
            },
            list(SOURCE),
        ),
        PAGE,
    ),
    "search_ledger_accounts": (obj({**BIND, "query": S}), obj({"accounts": array(S)})),
    "approve_import_prices": (
        obj(
            {
                **BIND,
                "run_id": ID,
                "expected_etag": HASH,
                "review_digest": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            }
        ),
        obj({"run_id": ID, "etag": HASH, "review_digest": S}),
    ),
    "update_import_review": (
        obj({**SOURCE, "update": UPDATE}),
        SAVED,
    ),
}
ERROR = obj({"status": {"const": "error"}, "error_code": S, "message": S})


def output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    success = obj({"status": {"const": "ok"}, "result": schema})
    change_fields = {
        "changed_files": array(S),
        "file_sha256": {"type": "object", "additionalProperties": HASH},
    }
    success["properties"].update(change_fields)
    error = copy.deepcopy(ERROR)
    error["properties"].update(change_fields)
    return {
        "type": "object",
        "oneOf": [success, error],
    }


def validate(schema: dict[str, Any], value: Any) -> None:
    error = next(
        Draft202012Validator(schema, format_checker=FORMATS).iter_errors(value), None
    )
    if error:
        invalid(
            f"Invalid tool payload at {list(error.absolute_path)}: {error.validator}."
        )


def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    validate(CONTRACTS[name][0], args)
    if name == "open_import_review":
        if ("workspace" in args) != ("session_id" in args):
            invalid("Provide both workspace and session ID.")
        if args:
            ReviewFiles(Path(args["workspace"]), args["session_id"]).read(
                f".auto-bean/import-sessions/{args['session_id']}.json"
            )
        return {"binding": args or None}
    if name == "export_import_review":
        from auto_bean.review_export import export_review_html

        return export_review_html(Path(args["workspace"]), args["session_id"])
    store = ReviewFiles(Path(args["workspace"]), args["session_id"])
    session = store.read(store.session_path)
    if name == "prepare_import_review_batch":
        return store.prepare_batch(args["token"])
    if name == "acknowledge_import_review_batch":
        return store.acknowledge_batch(args["pending_token"])
    if name == "read_import_session":
        status = load_state(checked_path(store.root, "statements/import-status.yml"))
        validate_state("status", store.root, status)
        session_status(session, status)
        statements = []
        for item in session_members(session):
            entry = status_members(status).get(item["source_file"], {})
            summary = {
                **item,
                "status": entry.get("current_status", "unavailable"),
                "updated_at": entry.get("updated_at"),
                "etag": None,
                "extraction_state": None,
                "needs_input": 0,
                "error": None,
            }
            try:
                if entry.get("parsed_group") != item["parsed_group"]:
                    invalid("Status pointer no longer matches this session.")
                doc = store.statement(item["source_file"])
                if (
                    doc["source_file"] != item["source_file"]
                    or doc["source_fingerprint"] != entry["source_fingerprint"]
                ):
                    invalid("Status and parsed source identity disagree.")
                review = doc["review"]
                summary.update(
                    etag=etag(doc),
                    extraction_state=doc["extraction_state"],
                    needs_input=int(review["processing"].get("needs_input", False))
                    + sum(
                        a["state"] == "needs_input"
                        for a in account_decisions(doc).values()
                    )
                    + sum(
                        t["state"] == "needs_input" or t["disposition"] == "hold"
                        for t in transaction_decisions(doc).values()
                    ),
                )
            except (WorkflowError, OSError) as error:
                summary["error"] = str(error)
            statements.append(summary)
        return {
            "workspace": str(store.root),
            "session_id": store.session_id,
            "etag": etag(session),
            "statements": statements,
            "review_batch": store.review_batch(),
            "groups": [
                {
                    **g,
                    "current_status": status["groups"][g["group_id"]]["current_status"],
                    "updated_at": status["groups"][g["group_id"]].get("updated_at"),
                }
                for g in session["groups"]
            ],
            "price_runs": [
                {
                    **run,
                    "review_digest": price_material(run),
                    "validation_current": validation_current(
                        store.root, price_material(run), run.get("validation")
                    ),
                }
                for run in session["price_runs"]
            ],
        }
    if name == "search_ledger_accounts":
        from beancount import loader
        from beancount.core.data import Open

        entries, errors, _ = loader.load_file(str(store.root / "ledger.beancount"))
        if errors:
            invalid("Canonical ledger is invalid; account search is unavailable.")
        return {
            "accounts": sorted(
                {
                    e.account
                    for e in entries
                    if isinstance(e, Open)
                    and args["query"].lower() in e.account.lower()
                }
            )[:100]
        }
    if name == "approve_import_prices":
        run = store.approve_prices(
            args["run_id"],
            args["expected_etag"],
            args["review_digest"],
        )
        return {
            "run_id": run["run_id"],
            "etag": etag(store.read(store.session_path)),
            "review_digest": run["approval"]["digest"],
        }
    source = args["source_file"]
    doc = store.statement(source)
    body = doc.get("review", doc)
    if name == "read_import_statement":
        return {
            **{
                k: doc[k]
                for k in (
                    "source_file",
                    "extraction_state",
                    "statement_metadata",
                )
            },
            "etag": etag(doc),
            "processing": body["processing"],
            "review_digest": material(doc),
            "approval": body.get("approval"),
            "validation": body.get("validation"),
            "validation_current": validation_current(
                store.root, material(doc), body.get("validation"), doc, store
            ),
        }
    if name == "list_import_transactions":
        rows = []
        for record in doc["extracted_records"]:
            decision = record.get("review", {})
            if args.get("account_id") and record["account_id"] != args["account_id"]:
                continue
            if (
                args.get("needs_input")
                and decision.get("state") != "needs_input"
                and decision.get("disposition") != "hold"
            ):
                continue
            rows.append(record)
        offset, limit = args.get("offset", 0), args.get("limit", 100)
        return {
            "etag": etag(doc),
            "total": len(rows),
            "offset": offset,
            "rows": rows[offset : offset + limit],
        }
    if name == "update_import_review":
        return store.submit(args["source_file"], args["update"])
    invalid("Unknown operation.")


@server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_tools() -> list[types.Tool]:
    result = []
    for name, (inputs, outputs) in CONTRACTS.items():
        meta: dict[str, Any] = {}
        if name == "open_import_review":
            meta = {
                "ui": {"resourceUri": URI},
                "openai/ui": {"entrypoints": [{"type": "thread"}]},
            }
        if name not in {"open_import_review", "export_import_review"}:
            meta = {"ui": {"visibility": ["app"]}}
        result.append(
            types.Tool(
                name=name,
                title="Import Review"
                if name == "open_import_review"
                else name.replace("_", " ").title(),
                description="Open the local import review panel."
                if name == "open_import_review"
                else f"{name.replace('_', ' ')}. Explicit workspace/session binding; strict v2 artifacts.",
                inputSchema={
                    **inputs,
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$id": f"https://auto-bean.local/schemas/v1/tools/{name}/input",
                },
                outputSchema={
                    **output_schema(outputs),
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "$id": f"https://auto-bean.local/schemas/v1/tools/{name}/output",
                },
                annotations=types.ToolAnnotations(
                    readOnlyHint=name
                    not in {
                        "update_import_review",
                        "acknowledge_import_review_batch",
                        "approve_import_prices",
                        "export_import_review",
                    },
                    destructiveHint=False,
                    openWorldHint=False,
                ),
                _meta=meta,
            )
        )
    return result


@server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl(URI), name="Import Review", mimeType="text/html;profile=mcp-app"
        )
    ]


@server.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
async def read_resource(uri: Any) -> list[ReadResourceContents]:
    if str(uri) != URI:
        invalid("Unknown UI resource.")
    return [
        ReadResourceContents(
            content=(PLUGIN / "ui/bundle.html").read_text(),
            mime_type="text/html;profile=mcp-app",
            meta={
                "ui": {"csp": {"connectDomains": [], "resourceDomains": []}},
                "openai/ui": {
                    "availableDisplayModes": ["fullscreen"],
                    "preferredDisplayMode": "fullscreen",
                },
            },
        )
    ]


@server.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
    with record_changes() as changes:
        try:
            if name not in CONTRACTS:
                invalid("Unknown tool.")
            value = await asyncio.to_thread(dispatch, name, arguments)
            result: dict[str, Any] = {"status": "ok", "result": value}
            validate(output_schema(CONTRACTS[name][1]), result)
        except (WorkflowError, OSError, ValueError) as error:
            result = {
                "status": "error",
                "error_code": getattr(error, "code", "read_failed"),
                "message": str(error),
            }
    result.update(change_report(Path(str(arguments.get("workspace", "."))), changes))
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(result))],
        structuredContent=result,
        isError=result["status"] == "error",
    )


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
