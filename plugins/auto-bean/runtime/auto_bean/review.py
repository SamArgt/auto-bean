"""Internal panel file access and content-checked submissions; not an agent editing API."""

from __future__ import annotations

import fcntl
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_bean.common import (
    WorkflowError,
    atomic_write,
    checked_path,
    digest,
    json_bytes,
    workspace,
)
from auto_bean.validation import (
    bounded_path,
    invalid,
    load_state,
    validate_state,
    session_members,
    session_status,
    status_members,
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        invalid("Invalid stable identifier.")
    return value


@contextmanager
def writer_lock(root: Path) -> Iterator[None]:
    path = checked_path(root, ".auto-bean/review.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def account_decisions(data: dict[str, Any]) -> dict[str, Any]:
    """Index inline account decisions without duplicating persisted evidence."""
    return {
        row["account_id"]: row["review"]
        for row in data["statement_metadata"]["accounts"]
        if "review" in row
    }


def transaction_decisions(data: dict[str, Any]) -> dict[str, Any]:
    """Index inline transaction decisions; unreviewed source rows remain absent."""
    return {
        row["record_id"]: row["review"]
        for row in data["extracted_records"]
        if "review" in row
    }


def material(data: dict[str, Any]) -> str:
    """Bind review to source facts and inline decisions, excluding progress/results."""
    result = {k: v for k, v in data.items() if k not in {"review"}}
    result["review"] = {
        "processing": {
            k: v
            for k, v in data["review"]["processing"].items()
            if k in {"needs_input", "suggestions", "answer"}
        }
    }
    return digest(json_bytes(result))


def price_material(run: dict[str, Any]) -> str:
    return digest(
        json_bytes(
            {k: v for k, v in run.items() if k not in {"approval", "validation"}}
        )
    )


def require_ready(document: dict[str, Any]) -> None:
    if document["extraction_state"] != "complete" or document["review"][
        "processing"
    ].get("needs_input"):
        invalid("Complete extraction and resolve processing input before review.")
    accounts = account_decisions(document)
    records = transaction_decisions(document)
    if len(accounts) != len(document["statement_metadata"]["accounts"]) or any(
        a["state"] == "needs_input" or not a.get("ledger_account")
        for a in accounts.values()
    ):
        invalid("Every extracted account needs a resolved mapping.")
    if len(records) != len(document["extracted_records"]) or any(
        r["state"] == "needs_input" or r["disposition"] == "hold"
        for r in records.values()
    ):
        invalid("Every extracted record needs a resolved disposition.")
    for row in document["extracted_records"]:
        decision = row["review"]
        if decision["disposition"] == "post" and not decision["postings"]:
            invalid("A posted record requires explicit postings.")


def etag(data: dict[str, Any]) -> str:
    """Content token detects direct file edits without agent-managed counters."""
    return digest(json_bytes(data))


class ReviewFiles:
    def __init__(self, root: Path, session_id: str):
        self.root = workspace(root)
        self.session_id = identifier(session_id)
        self.session_path = f".auto-bean/import-sessions/{session_id}.json"

    def read(self, path: str) -> dict[str, Any]:
        kind = "session" if path == self.session_path else "parsed-group"
        bounded_path(
            self.root,
            path,
            ".auto-bean/import-sessions" if kind == "session" else "statements/parsed",
        )
        data = load_state(checked_path(self.root, path))
        validate_state(kind, self.root, data)
        if kind == "session":
            if data["session_id"] != self.session_id:
                invalid("Session identity disagrees with its filename.")
        else:
            session = self.read(self.session_path)
            group = next(
                (g for g in session["groups"] if g["parsed_group"] == path), None
            )
            if (
                group is None
                or group["group_id"] != data["group_id"]
                or set(group["source_files"])
                != {d["source_file"] for d in data["statements"]}
            ):
                invalid("Parsed group identity or membership is outside this session.")
            for statement in data["statements"]:
                entry = self.status_entry(statement["source_file"], path)
                if entry["source_fingerprint"] != statement["source_fingerprint"]:
                    invalid("Parsed source fingerprint disagrees with status.")
        return data

    def statement(self, source: str) -> dict[str, Any]:
        group = self.read(self.statement_path(source))
        return next(d for d in group["statements"] if d["source_file"] == source)

    def status_entry(self, source: str, path: str) -> dict[str, Any]:
        status = load_state(checked_path(self.root, "statements/import-status.yml"))
        validate_state("status", self.root, status)
        session_status(self.read(self.session_path), status)
        entry: dict[str, Any] = status_members(status).get(source, {})
        if entry.get("parsed_group") != path:
            invalid("Session membership no longer matches its group status entry.")
        return entry

    def _publish(self, path: str, data: dict[str, Any], expected: str) -> None:
        validate_state(
            "session" if path == self.session_path else "parsed-group", self.root, data
        )
        if etag(self.read(path)) != expected:
            raise WorkflowError(
                "edit_conflict",
                "Artifact changed during this operation; refresh and retry.",
            )
        atomic_write(checked_path(self.root, path), json_bytes(data))

    def _publish_statement(
        self, source: str, data: dict[str, Any], expected: str
    ) -> None:
        path = self.statement_path(source)
        group = self.read(path)
        token = etag(group)
        index = next(
            i for i, d in enumerate(group["statements"]) if d["source_file"] == source
        )
        if etag(group["statements"][index]) != expected:
            raise WorkflowError(
                "edit_conflict",
                "Statement changed during this operation; refresh and retry.",
            )
        group["statements"][index] = data
        self._publish(path, group, token)

    def statement_path(self, source: str) -> str:
        for item in session_members(self.read(self.session_path)):
            if item["source_file"] == source:
                path: str = item["parsed_group"]
                self.status_entry(source, path)
                return path
        invalid("Statement is not a member of this session.")

    def approve_prices(
        self, run_id: str, expected_etag: str, review_digest: str
    ) -> dict[str, Any]:
        with writer_lock(self.root):
            data = self.read(self.session_path)
            if etag(data) != expected_etag:
                raise WorkflowError(
                    "edit_conflict", "Session changed; refresh price results."
                )
            run = next((r for r in data["price_runs"] if r["run_id"] == run_id), None)
            if run is None or price_material(run) != review_digest:
                raise WorkflowError(
                    "review_conflict",
                    "Price results changed; review the current directives.",
                )
            if run["state"] not in {"complete", "no_op", "partial"}:
                invalid("Price results are not ready for review.")
            run["approval"] = {
                "digest": review_digest,
                "approved_at": now(),
                "origin": "panel",
            }
            self._publish(self.session_path, data, expected_etag)
            self.record_batch("price run " + run_id, "approval", run["approval"])
            return dict(run)

    @property
    def batch_path(self) -> Path:
        return checked_path(
            self.root, f".auto-bean/review-batches/{self.session_id}.json"
        )

    def batch_receipts(self) -> dict[str, Any]:
        if not self.batch_path.exists():
            return {"receipts": {}, "pending": {}}
        data = load_state(self.batch_path)
        if not isinstance(data.get("receipts"), dict) or not isinstance(
            data.get("pending"), dict
        ):
            invalid("Invalid review batch bookkeeping.")
        return data

    def record_batch(self, source: str, subject: str, value: Any) -> None:
        """Called under the writer lock after the canonical artifact is saved."""
        batch = self.batch_receipts()
        key = source + "#" + subject
        batch["receipts"][key] = etag({"value": value})
        batch["pending"][key] = {"source": source, "subject": subject}
        self.batch_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.batch_path, json_bytes(batch))

    def review_batch(self) -> dict[str, Any]:
        batch = self.batch_receipts()
        receipts = batch["receipts"]
        blockers: list[str] = []
        snapshots: dict[str, str] = {}
        session = self.read(self.session_path)

        def reviewed(source: str, subject: str, value: Any) -> bool:
            return bool(receipts.get(source + "#" + subject) == etag({"value": value}))

        for member in session_members(session):
            source = member["source_file"]
            try:
                status = self.status_entry(source, member["parsed_group"])[
                    "current_status"
                ]
                if status == "done":
                    continue
                if (
                    status == "raw_ready"
                    and not checked_path(self.root, member["parsed_group"]).exists()
                ):
                    # Extraction has not produced review inputs for this group yet.
                    snapshots[source] = "awaiting extraction"
                    continue
                doc = self.statement(source)
                snapshots[source] = etag(doc)
                processing = doc["review"]["processing"]
                if processing.get("needs_input") and not reviewed(
                    source, "statement", processing
                ):
                    blockers.append(source + ": source input")
                for account in doc["statement_metadata"]["accounts"]:
                    if account.get("review", {}).get(
                        "state"
                    ) == "needs_input" and not reviewed(
                        source, "account:" + account["account_id"], account
                    ):
                        blockers.append(source + ": account " + account["account_id"])
                for row in doc["extracted_records"]:
                    decision = row.get("review", {})
                    if (
                        decision.get("state") == "needs_input"
                        or decision.get("disposition") == "hold"
                    ) and not reviewed(source, "transaction:" + row["record_id"], row):
                        blockers.append(source + ": transaction " + row["record_id"])
                try:
                    require_ready(doc)
                    approval_available = True
                except WorkflowError:
                    approval_available = False
                if (
                    approval_available
                    and status == "final_review"
                    and doc["review"].get("approval", {}).get("digest") != material(doc)
                    and not reviewed(source, "decision", material(doc))
                ):
                    blockers.append(source + ": statement approval")
            except (WorkflowError, OSError) as error:
                blockers.append(source + ": " + str(error))
        for run in session["price_runs"]:
            if any(
                j.get("outcome") == "emitted" for j in run.get("jobs", [])
            ) and run.get("approval", {}).get("digest") != price_material(run):
                blockers.append("Price run " + run["run_id"] + ": approval")
        pending = list(batch["pending"].values())
        return {
            "pending_count": len(pending),
            "pending_token": etag(batch),
            "token": etag(
                {
                    "batch": batch,
                    "session": session,
                    "snapshots": snapshots,
                    "blockers": blockers,
                }
            ),
            "blockers": blockers,
            "ready": bool(pending) and not blockers,
            "subjects": sorted({p["source"] for p in pending}),
        }

    def prepare_batch(self, token: str) -> dict[str, Any]:
        with writer_lock(self.root):
            batch = self.review_batch()
            if batch["token"] != token or not batch["ready"]:
                raise WorkflowError(
                    "review_conflict",
                    "Review inputs changed or remain unanswered. Refresh before sending.",
                )
            return batch

    def acknowledge_batch(self, pending_token: str) -> dict[str, Any]:
        with writer_lock(self.root):
            batch = self.batch_receipts()
            if etag(batch) != pending_token:
                # A newer save must survive acknowledgement of an older batch.
                return self.review_batch()
            batch["pending"] = {}
            atomic_write(self.batch_path, json_bytes(batch))
            return self.review_batch()

    def check_links(self, sources: list[str] | None = None) -> None:
        session = self.read(self.session_path)
        paths = {i["source_file"]: i["parsed_group"] for i in session_members(session)}
        selected = sources if sources is not None else list(paths)
        documents = {source: self.statement(source) for source in selected}

        def linked(source: str) -> dict[str, Any] | None:
            if source not in paths:
                return None
            if source not in documents:
                documents[source] = self.statement(source)
            return documents[source]

        for source in selected:
            doc = documents[source]
            for record_id, decision in transaction_decisions(doc).items():
                for link in decision.get("linked_records", []):
                    other = linked(link["source_file"])
                    if other is None or not any(
                        r["record_id"] == link["record_id"]
                        and r["account_id"] == link["account_id"]
                        for r in other["extracted_records"]
                    ):
                        invalid(
                            "Cross-statement record is missing or outside this session."
                        )
                    if decision["disposition"] == "paired_transfer":
                        peer = transaction_decisions(other).get(link["record_id"], {})
                        if (
                            peer.get("disposition") != "paired_transfer"
                            or peer.get("posting_owner") != decision["posting_owner"]
                            or not any(
                                back["source_file"] == doc["source_file"]
                                and back["record_id"] == record_id
                                and back["account_id"]
                                == next(
                                    r["account_id"]
                                    for r in doc["extracted_records"]
                                    if r["record_id"] == record_id
                                )
                                for back in peer.get("linked_records", [])
                            )
                            or decision["posting_owner"]
                            not in {source, link["source_file"]}
                            or (
                                source == link["source_file"]
                                and record_id == link["record_id"]
                            )
                        ):
                            invalid("Transfer cohort has conflicting ownership.")

    def submit(self, source: str, update: dict[str, Any]) -> dict[str, Any]:
        """Save an explicit user edit or confirmation in place; no action queue."""
        permitted = {
            "kind",
            "subject_id",
            "subject_kind",
            "value",
            "review_digest",
            "expected_etag",
        }
        if update.keys() - permitted:
            invalid("Update contains undeclared fields.")
        if not {"kind", "subject_id", "expected_etag"} <= update.keys():
            invalid("Update kind, subject and expected content token are required.")
        with writer_lock(self.root):
            path = self.statement_path(source)
            data = self.statement(source)
            if update["expected_etag"] != etag(data):
                raise WorkflowError(
                    "edit_conflict",
                    "Review changed; refresh and resubmit your retained edit.",
                )
            if self.status_entry(source, path)["current_status"] == "done":
                invalid(
                    "Completed statements require explicit rework before correction."
                )
            body, kind, subject = data["review"], update["kind"], update["subject_id"]
            if kind in {"approve", "reject"}:
                if subject != "statement" or update.get("review_digest") != material(
                    data
                ):
                    raise WorkflowError(
                        "review_conflict",
                        "Reviewed transactions changed; review the current data.",
                    )
                if kind == "approve":
                    require_ready(data)
                    self.check_links([source])
                    if (
                        "sha256:" + digest(checked_path(self.root, source).read_bytes())
                        != data["source_fingerprint"]
                    ):
                        invalid("Raw source changed after extraction.")
                    body["approval"] = {
                        "digest": material(data),
                        "approved_at": now(),
                        "origin": "panel",
                    }
                else:
                    body.pop("approval", None)
            else:
                if kind == "answer":
                    block = (
                        body["processing"]
                        if update.get("subject_kind") == "statement"
                        and subject == "statement"
                        else account_decisions(data).get(subject)
                        if update.get("subject_kind") == "account"
                        else transaction_decisions(data).get(subject)
                        if update.get("subject_kind") == "transaction"
                        else None
                    )
                    if (
                        block is None
                        or not isinstance(update.get("value"), str)
                        or not update["value"].strip()
                    ):
                        invalid("An answer requires a known subject and nonempty text.")
                    block["answer"] = update["value"]
                    if block is body["processing"]:
                        block["needs_input"] = True
                    else:
                        block["state"] = "needs_input"
                elif kind == "mapping":
                    block = account_decisions(data).get(subject)
                    if (
                        block is None
                        or not isinstance(update.get("value"), str)
                        or not re.fullmatch(
                            r"(Assets|Liabilities|Equity|Income|Expenses)(:[A-Z][A-Za-z0-9-]*)+",
                            update["value"],
                        )
                    ):
                        invalid(
                            "Mapping requires an existing account and valid ledger account name."
                        )
                    block.update(ledger_account=update["value"], state="needs_input")
                elif kind == "postings":
                    block = transaction_decisions(data).get(subject)
                    if (
                        block is None
                        or not isinstance(update.get("value"), list)
                        or not update["value"]
                    ):
                        invalid(
                            "Correction requires a transaction and explicit postings."
                        )
                    block.update(postings=update["value"], state="needs_input")
                else:
                    invalid("Unsupported review update.")
                body.pop("approval", None)
            body.pop("validation", None)
            self._publish_statement(source, data, update["expected_etag"])
            if kind in {"approve", "reject"}:
                self.record_batch(source, "decision", material(data))
            elif kind == "answer" and update.get("subject_kind") == "statement":
                self.record_batch(source, "statement", body["processing"])
            elif kind == "mapping" or update.get("subject_kind") == "account":
                account = next(
                    a
                    for a in data["statement_metadata"]["accounts"]
                    if a["account_id"] == subject
                )
                self.record_batch(source, "account:" + subject, account)
            else:
                row = next(
                    r for r in data["extracted_records"] if r["record_id"] == subject
                )
                self.record_batch(source, "transaction:" + subject, row)
            return {
                "source_file": source,
                "etag": etag(data),
                "review_digest": material(data),
            }
