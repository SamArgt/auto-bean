"""Generate closed import-review schemas from the normalized evidence contract."""

from __future__ import annotations
import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1] / "plugins/auto-bean/references"
S = {"type": "string"}
ID = {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}
DATE = {"type": "string", "format": "date"}
TIME = {"type": "string", "format": "date-time"}
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
DEC = {"type": "string", "pattern": r"^[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)$"}
INT = {"type": "integer", "minimum": 0}


def obj(
    properties: dict[str, Any], required: list[str] | None = None
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


def arr(item: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": item}


def enum(*values: str) -> dict[str, Any]:
    return {"enum": list(values)}


def mapping(item: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "propertyNames": ID, "additionalProperties": item}


def nullable(item: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [item, {"type": "null"}]}


def close(value: Any) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object":
            value["additionalProperties"] = False
        for child in value.values():
            close(child)
    elif isinstance(value, list):
        for child in value:
            close(child)


def schemas() -> dict[str, Any]:
    link = obj({"source_file": S, "account_id": ID, "record_id": ID})
    posting = obj(
        {"account": S, "amount": DEC, "currency": S, "cost": S, "price": S},
        ["account", "amount", "currency"],
    )
    approval = obj({"digest": HASH, "approved_at": TIME, "origin": enum("panel")})
    validation = obj(
        {
            "state": enum("passed", "failed"),
            "stage": enum("review", "written"),
            "checked_at": TIME,
            "digest": HASH,
            "ledger_hashes": {"type": "object", "additionalProperties": HASH},
            "records_checked": INT,
            "balances": arr(
                obj(
                    {
                        "account_id": ID,
                        "date": DATE,
                        "currency": S,
                        "expected": DEC,
                        "actual": DEC,
                        "state": enum("matched", "mismatch"),
                    }
                )
            ),
            "errors": arr(S),
        }
    )
    review = obj(
        {
            "processing": obj(
                {
                    "attempts": INT,
                    "outcome": enum("pending", "running", "failed", "complete"),
                    "warnings": arr(S),
                    "evidence": arr(S),
                    "failure_reason": S,
                    "needs_input": {"type": "boolean"},
                    "suggestions": arr(S),
                    "answer": {"type": "string", "minLength": 1},
                    "failure_code": enum(
                        "tool_timeout",
                        "transient_io_failure",
                        "parser_crash",
                        "malformed_parser_output",
                        "unsupported_format",
                        "encrypted_or_unreadable_source",
                        "textless_pdf",
                        "missing_source",
                        "tool_unavailable",
                    ),
                },
                ["attempts", "outcome", "warnings", "evidence"],
            ),
            "accounts": mapping(
                obj(
                    {
                        "state": enum("proposed", "confirmed", "needs_input"),
                        "ledger_account": S,
                        "rationale": S,
                        "suggestions": arr(S),
                        "answer": {"type": "string", "minLength": 1},
                        "proposed_directives": arr(S),
                        "reconciliation": arr(
                            obj(
                                {
                                    "date": DATE,
                                    "currency": S,
                                    "ledger_amount": DEC,
                                    "difference": DEC,
                                    "provenance": S,
                                    "state": enum("matched", "mismatch", "unavailable"),
                                },
                                ["date", "currency", "provenance", "state"],
                            )
                        ),
                    },
                    ["state", "rationale"],
                )
            ),
            "transactions": mapping(
                obj(
                    {
                        "state": enum("proposed", "confirmed", "needs_input"),
                        "postings": arr(posting),
                        "rationale": S,
                        "suggestions": arr(S),
                        "answer": {"type": "string", "minLength": 1},
                        "findings": arr(
                            enum(
                                "likely_transfer",
                                "possible_future_transfer",
                                "possible_duplicate",
                                "unbalanced",
                                "currency_risk",
                            )
                        ),
                        "disposition": enum(
                            "post", "existing_duplicate", "paired_transfer", "hold"
                        ),
                        "linked_records": arr(link),
                        "existing_transaction": obj(
                            {
                                "path": S,
                                "line": {"type": "integer", "minimum": 1},
                            }
                        ),
                        "posting_owner": S,
                    },
                    [
                        "state",
                        "postings",
                        "rationale",
                        "disposition",
                    ],
                )
            ),
            "approval": approval,
            "validation": validation,
        }
    )
    account_review = review["properties"].pop("accounts")["additionalProperties"]
    transaction_review = review["properties"].pop("transactions")[
        "additionalProperties"
    ]
    review["required"] = ["processing"]
    parsed = copy.deepcopy(
        json.loads((ROOT / "schemas/parsed.schema.json").read_text())
    )
    close(parsed)
    parsed["$id"] = "https://auto-bean.local/schemas/v2/parsed"
    props = parsed["properties"]
    props.pop("process_artifact")
    props["schema_version"] = {"const": 2}
    props["extraction_state"] = enum("pending", "running", "failed", "complete")
    props["review"] = review
    props["parser"]["properties"].update({"mode": S, "version": S})
    meta = props["statement_metadata"]["properties"]
    meta.update(
        {
            "institution_name": S,
            "statement_name": S,
            "issued_date": DATE,
            "account_owner": S,
            "account_names": arr(S),
        }
    )
    meta["accounts"]["items"]["properties"].update(
        {
            "account_id": ID,
            "account_owner": S,
            "account_type": S,
            "institution_name": S,
            "account_number": S,
            "review": account_review,
        }
    )
    record = props["extracted_records"]["items"]["properties"]
    record["account_id"] = ID
    record["record_id"] = ID
    record["payee"] = S
    record["review"] = transaction_review
    record["raw_fields"] = {
        "type": "object",
        "additionalProperties": {"type": ["string", "number", "boolean", "null"]},
    }
    parsed["required"] = [
        "schema_version",
        "extraction_state",
        "source_file",
        "source_fingerprint",
        "source_format",
        "statement_metadata",
        "extracted_records",
        "review",
    ]
    parsed["allOf"] = [
        {
            "if": {"properties": {"extraction_state": {"const": "complete"}}},
            "then": {
                "required": ["parse_run_id", "parser", "parsed_at", "document_kind"]
            },
        }
    ]
    price = obj(
        {
            "run_id": ID,
            "requested_date": DATE,
            "state": enum(
                "pending", "running", "complete", "no_op", "failed", "partial"
            ),
            "required_commodities": arr(S),
            "coverage": arr(S),
            "preflight": enum("pending", "passed", "failed"),
            "preflight_job_count": INT,
            "execution": obj(
                {
                    "state": enum("pending", "running", "complete", "timed_out"),
                    "exit_code": nullable({"type": "integer"}),
                    "duration_seconds": {"type": "number", "minimum": 0},
                    "started_at": TIME,
                    "ended_at": TIME,
                    "stderr_summary": S,
                },
                ["state", "exit_code", "duration_seconds", "stderr_summary"],
            ),
            "jobs": arr(
                obj(
                    {
                        "commodity": S,
                        "source": S,
                        "requested_date": DATE,
                        "quote_date": DATE,
                        "outcome": enum(
                            "emitted", "redundant", "skipped", "failed", "unaccounted"
                        ),
                        "directive": S,
                        "detail": S,
                    },
                    ["commodity", "source", "requested_date", "outcome"],
                )
            ),
            "detail": S,
            "approval": approval,
            "validation": validation,
        },
        [
            "run_id",
            "requested_date",
            "state",
            "required_commodities",
            "coverage",
            "preflight",
            "preflight_job_count",
            "execution",
            "jobs",
            "detail",
        ],
    )
    session = obj(
        {
            "schema_version": {"const": 1},
            "session_id": ID,
            "created_at": TIME,
            "groups": arr(
                obj(
                    {
                        "group_id": ID,
                        "parsed_group": S,
                        "name": {"type": "string", "pattern": r"\S"},
                        "origin": enum("user", "agent"),
                        "source_files": {
                            **arr(S),
                            "minItems": 1,
                            "uniqueItems": True,
                        },
                    }
                )
            ),
            "price_runs": arr(price),
        }
    )
    session.update(
        {
            "$schema": parsed["$schema"],
            "$id": "https://auto-bean.local/schemas/v1/session",
        }
    )
    group_parsed = obj(
        {
            "schema_version": {"const": 2},
            "group_id": ID,
            "statements": {**arr(parsed), "minItems": 1},
        }
    )
    group_parsed.update(
        {
            "$schema": parsed["$schema"],
            "$id": "https://auto-bean.local/schemas/parsed-group",
        }
    )
    status = obj(
        {
            "version": {"const": 1},
            "groups": mapping(
                obj(
                    {
                        "session_id": ID,
                        "current_status": enum(
                            "raw_ready",
                            "process_blocked",
                            "process_review",
                            "account_review",
                            "account_blocked",
                            "balance_review",
                            "balance_blocked",
                            "categorize_ready",
                            "categorize_blocked",
                            "categorize_review",
                            "write_ready",
                            "write_blocked",
                            "final_review",
                            "done",
                        ),
                        "parsed_group": S,
                        "updated_at": TIME,
                        "user_input_required": {"type": "boolean"},
                        "manual_resolution_required": {"type": "boolean"},
                        "sources": {
                            "type": "object",
                            "minProperties": 1,
                            "additionalProperties": obj(
                                {
                                    "source_fingerprint": {
                                        "type": "string",
                                        "pattern": "^sha256:[0-9a-f]{64}$",
                                    },
                                    "process_attempts": INT,
                                    "last_process_failure_reason": {
                                        "type": ["string", "null"]
                                    },
                                },
                                ["source_fingerprint"],
                            ),
                        },
                    },
                    ["session_id", "current_status", "parsed_group", "sources"],
                )
            ),
        }
    )
    status.update(
        {
            "$schema": parsed["$schema"],
            "$id": "https://auto-bean.local/schemas/v1/status",
        }
    )
    return {
        "parsed-v2": parsed,
        "parsed-group": group_parsed,
        "session": session,
        "status": status,
    }


def main() -> None:
    for name, schema in schemas().items():
        (ROOT / f"schemas/{name}.schema.json").write_text(
            json.dumps(schema, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
