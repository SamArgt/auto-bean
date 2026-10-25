"""Generate closed import-review schemas from the normalized evidence contract."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1] / "plugins/auto-bean/references"
S = {"type": "string"}
ID = {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"}
DATE = {"type": "string", "format": "date"}
TIME = {"type": "string", "format": "date-time"}
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


def schemas() -> dict[str, Any]:
    # The statement schema is authored directly. Embed it in each group so
    # packaged validation does not need external schema resolution.
    parsed = json.loads((ROOT / "schemas/parsed-statement.schema.json").read_text())
    review = parsed["properties"]["review"]["properties"]
    approval = review["approval"]
    validation = review["validation"]
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
