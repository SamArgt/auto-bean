"""Loopback-only prototype server. Saves synthetic copies, never a user ledger."""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import threading
import uuid
from datetime import UTC, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import jsonschema

ROOT = Path(__file__).resolve().parent
SCHEMAS = ROOT.parents[1] / "plugins/auto-bean/references/schemas"
LOCK = threading.Lock()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(dump(value))
    temp.replace(path)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class DemoStore:
    def __init__(self, stage: str, root: Path = ROOT):
        if stage not in {"transactions", "accounts", "mixed"}:
            raise ValueError("Unknown fixture stage")
        self.stage, self.root = stage, root
        self.seed = root / "fixtures" / (stage if stage != "transactions" else "")
        self.path = root / ".demo-state" / stage
        if not (self.path / "batch.json").exists():
            self.reset()

    def reset(self) -> dict[str, Any]:
        session = read(self.seed / "session.json")
        for path in ["session.json", "import-status.json"] + [
            g["parsed_group"] for g in session["groups"]
        ]:
            write(self.path / path, read(self.seed / path))
        write(
            self.path / "batch.json",
            {
                "token": uuid.uuid4().hex,
                "pending": {},
                "answers": {},
                "approvals": [],
                "notifications": 0,
                "history": [],
            },
        )
        return self.state()

    def state(self) -> dict[str, Any]:
        session = read(self.path / "session.json")
        return {
            "session": session,
            "status": read(self.path / "import-status.json"),
            "documents": [
                read(self.path / g["parsed_group"]) for g in session["groups"]
            ],
            "batch": read(self.path / "batch.json"),
            "directory": str(self.path),
        }

    def save(self, request: dict[str, Any]) -> dict[str, Any]:
        state = self.state()
        batch = state["batch"]
        if request.get("expected_token") != batch["token"]:
            raise ValueError("Saved JSON changed. Reload before saving.")
        before_batch = copy.deepcopy(batch)
        subject, value = request["subject"], request.get("value")
        source = request.get("source_file")
        if source:
            group = next(
                (g for g in state["session"]["groups"] if source in g["source_files"]),
                None,
            )
            if not group:
                raise ValueError("Unknown statement")
            path = group["parsed_group"]
            doc = read(self.path / path)
            before = copy.deepcopy(doc)
            statement = next(s for s in doc["statements"] if s["source_file"] == source)
            review = statement["review"]
            key = source + "#" + subject
            if subject == "approval":
                review["approval"] = {
                    "digest": fingerprint(statement),
                    "approved_at": datetime.now(UTC).isoformat(),
                    "origin": "panel",
                }
                if source not in batch["approvals"]:
                    batch["approvals"].append(source)
            else:
                if subject == "source":
                    block = review["processing"]
                    block["answer"], block["needs_input"] = value, True
                elif subject.startswith("account:"):
                    account = next(
                        a
                        for a in statement["statement_metadata"]["accounts"]
                        if a["account_id"] == subject.split(":", 1)[1]
                    )
                    block = account["review"]
                    if any(
                        r["state"] == "mismatch"
                        for r in block.get("reconciliation", [])
                    ):
                        block["answer"] = value
                    else:
                        block["ledger_account"] = value
                    block["state"] = "needs_input"
                elif subject.startswith(("row:", "postings:")):
                    row = next(
                        r
                        for r in statement["extracted_records"]
                        if r["record_id"] == subject.split(":", 1)[1]
                    )
                    row["review"][
                        "postings" if subject.startswith("postings:") else "answer"
                    ] = value
                    row["review"]["state"] = "needs_input"
                else:
                    raise ValueError("Unknown save subject")
                batch["answers"][
                    source + "#" + subject.replace("postings:", "row:")
                ] = "Postings updated" if subject.startswith("postings:") else value
                review.pop("approval", None)
                review.pop("validation", None)
                batch["pending"].pop(source + "#approval", None)
                batch["approvals"] = [s for s in batch["approvals"] if s != source]
            schema = "parsed-group"
        else:
            path, schema = "session.json", "session"
            doc = state["session"]
            before = copy.deepcopy(doc)
            if subject != "approval":
                raise ValueError("Unknown price action")
            run = next(
                r for r in doc["price_runs"] if r["run_id"] == request.get("run_id")
            )
            key = "price:" + run["run_id"]
            run["approval"] = {
                "digest": fingerprint(run),
                "approved_at": datetime.now(UTC).isoformat(),
                "origin": "panel",
            }
        jsonschema.Draft202012Validator(
            read(SCHEMAS / f"{schema}.schema.json")
        ).validate(doc)
        batch["pending"][key] = {
            "source_file": source,
            "subject": subject,
            "value": value,
        }
        batch["history"].append(
            {
                "number": len(batch["history"]) + 1,
                "bookkeeping_diff": "".join(
                    difflib.unified_diff(
                        dump(
                            {
                                k: before_batch[k]
                                for k in ("pending", "answers", "approvals")
                            }
                        ).splitlines(True),
                        dump(
                            {k: batch[k] for k in ("pending", "answers", "approvals")}
                        ).splitlines(True),
                        fromfile="Before / batch.json",
                        tofile="After / batch.json",
                    )
                ),
                "path": path,
                "subject": subject,
                "diff": "".join(
                    difflib.unified_diff(
                        dump(before).splitlines(True),
                        dump(doc).splitlines(True),
                        fromfile="Before / " + path,
                        tofile="After / " + path,
                    )
                ),
            }
        )
        batch["token"] = uuid.uuid4().hex
        write(self.path / path, doc)
        write(self.path / "batch.json", batch)
        return self.state()

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        state = self.state()
        batch = state["batch"]
        if request.get("expected_token") != batch["token"] or not batch["pending"]:
            raise ValueError("Batch changed or is empty")
        # Repeat the browser gate against persisted JSON before simulated sending.
        for group in state["documents"]:
            for statement in group["statements"]:
                source = statement["source_file"]
                needed = []
                if statement["review"]["processing"].get("needs_input"):
                    needed.append("source")
                needed.extend(
                    "account:" + a["account_id"]
                    for a in statement["statement_metadata"]["accounts"]
                    if a.get("review", {}).get("state") == "needs_input"
                )
                needed.extend(
                    "row:" + r["record_id"]
                    for r in statement["extracted_records"]
                    if r.get("review", {}).get("state") == "needs_input"
                    or r.get("review", {}).get("disposition") == "hold"
                )
                if any(
                    source + "#" + key not in batch["answers"]
                    and source + "#" + key.replace("row:", "postings:")
                    not in batch["pending"]
                    for key in needed
                ):
                    raise ValueError("Current inputs still need review")
                accounts = statement["statement_metadata"]["accounts"]
                rows = statement["extracted_records"]
                status = state["status"]["groups"][group["group_id"]]["current_status"]
                available = (
                    statement["extraction_state"] == "complete"
                    and (
                        bool(rows)
                        or status.startswith(("categorize_", "write_", "final_review"))
                    )
                    and all(
                        r.get("review")
                        and r["review"].get("state") != "needs_input"
                        and r["review"].get("disposition") != "hold"
                        for r in rows
                    )
                    and all(
                        a.get("review", {}).get("ledger_account")
                        and a["review"].get("state") != "needs_input"
                        for a in accounts
                    )
                )
                if available and source not in batch["approvals"]:
                    raise ValueError("Statement approval still needed")
        for run in state["session"]["price_runs"]:
            if any(
                j["outcome"] == "emitted" for j in run.get("jobs", [])
            ) and not run.get("approval"):
                raise ValueError("Price approval still needed")
        batch["last_sent"] = batch["pending"]
        batch["pending"] = {}
        batch["notifications"] += 1
        batch["token"] = uuid.uuid4().hex
        write(self.path / "batch.json", batch)
        return self.state()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def result(self, value: Any, status: int = 200) -> None:
        body = dump(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        if url.path == "/api/state":
            try:
                with LOCK:
                    self.result(
                        DemoStore(
                            parse_qs(url.query).get("stage", ["transactions"])[0]
                        ).state()
                    )
            except (ValueError, OSError) as error:
                self.result({"error": str(error)}, 400)
        elif url.path.startswith("/.demo-state/"):
            self.send_error(403)
        else:
            super().do_GET()

    def do_POST(self) -> None:
        # Restrict mutations to this loopback page, including protection from cross-site forms.
        if (
            self.headers.get("Origin") != "http://" + self.headers.get("Host", "")
            or self.headers.get("Content-Type") != "application/json"
        ):
            self.result({"error": "Same-origin JSON requests required"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2_000_000:
                raise ValueError("Invalid request size")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("Expected an object")
            with LOCK:
                store = DemoStore(request.get("stage", "transactions"))
                if self.path == "/api/save":
                    value = store.save(request)
                elif self.path == "/api/reset":
                    value = store.reset()
                elif self.path == "/api/send":
                    value = store.send(request)
                else:
                    raise ValueError("Unknown action")
                self.result(value)
        except (
            ValueError,
            KeyError,
            StopIteration,
            OSError,
            jsonschema.ValidationError,
        ) as error:
            self.result({"error": str(error)}, 409)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
