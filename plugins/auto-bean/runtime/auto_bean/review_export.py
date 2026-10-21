"""Portable, read-only HTML snapshots of one explicitly selected import session."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from auto_bean.common import WorkflowError, atomic_write, checked_path, digest
from auto_bean.review import (
    ReviewFiles,
    etag,
    material,
    now,
    price_material,
    writer_lock,
)
from auto_bean.validation import invalid, load_state, validate_state

CSS = """
:root{font:14px/1.5 system-ui,sans-serif;color:#202624;background:#f8faf8}
*{box-sizing:border-box}body{margin:0}main{max-width:1100px;margin:auto;padding:24px}
header{border-bottom:1px solid #87968b55;padding-bottom:16px}h1{font-size:26px}
h2{font-size:21px;margin-top:28px}h3{font-size:17px}h4{font-size:15px;margin:0 0 8px}
p{margin:8px 0}.eyebrow{font-size:11px;letter-spacing:2px;color:#65796d}
.context,.muted,footer{font-size:12px;color:#67706b;overflow-wrap:anywhere}
.card,details{border:1px solid #87968b55;border-radius:8px;padding:16px;margin:12px 0;background:#fff}
.needs{border-color:#a76b12;background:#fff8e9}.notice{padding:12px;background:#eaf3ec;border-radius:6px}
.error{padding:12px;background:#ffecea;border:1px solid #bb4336;border-radius:6px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef2ee;padding:12px;border-radius:6px}
table{width:100%;border-collapse:collapse}th,td{padding:8px;text-align:left;vertical-align:top;border-bottom:1px solid #87968b44;overflow-wrap:anywhere}
nav{display:flex;gap:16px;flex-wrap:wrap;padding:16px 0}a{color:#246644}
summary{cursor:pointer;font-weight:600}dl{display:grid;grid-template-columns:minmax(120px,1fr) 3fr;gap:6px}dd{margin:0}
@media print{body{background:white}main{max-width:none;padding:0}details{break-inside:avoid}a{color:inherit}}
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def readable(value: object) -> str:
    return esc(str(value).replace("_", " "))


def pretty(value: object) -> str:
    return "<pre>" + esc(json.dumps(value, indent=2, ensure_ascii=False)) + "</pre>"


def paragraph(value: object, css: str = "") -> str:
    return f'<p class="{css}">{esc(value)}</p>'


def details(title: str, value: object) -> str:
    return f"<details><summary>{esc(title)}</summary>{pretty(value)}</details>"


def validation_current(
    root: Path,
    evidence_digest: str,
    report: dict[str, Any] | None,
    document: dict[str, Any] | None = None,
    files: ReviewFiles | None = None,
) -> bool | None:
    """Derive freshness for display without changing saved validation evidence."""
    if report is None:
        return None
    if report["digest"] != evidence_digest:
        return False
    from auto_bean.reconciliation import financial_files

    try:
        if (
            document is not None
            and "sha256:"
            + digest(checked_path(root, document["source_file"]).read_bytes())
            != document["source_fingerprint"]
        ):
            return False
        hashes = financial_files(root)
        if report["ledger_hashes"] != hashes:
            return False
        if document is not None and files is not None:
            files.check_links([document["source_file"]])
            peers = {
                link["source_file"]
                for row in document["extracted_records"]
                for link in row.get("review", {}).get("linked_records", [])
                if link["source_file"] != document["source_file"]
            }
            for source in peers:
                peer = files.read(files.statement_path(source))
                result = peer["review"].get("validation")
                if (
                    not result
                    or result["state"] != "passed"
                    or result["stage"] != report["stage"]
                    or result["digest"] != material(peer)
                    or result["ledger_hashes"] != hashes
                    or "sha256:" + digest(checked_path(root, source).read_bytes())
                    != peer["source_fingerprint"]
                ):
                    return False
        return True
    except (WorkflowError, OSError, ValueError):
        return False


def _snapshot(store: ReviewFiles, exported_at: str) -> dict[str, Any]:
    """Caller holds the shared writer lock while reading all selected documents."""
    session = store.read(store.session_path)
    status = load_state(checked_path(store.root, "statements/import-status.yml"))
    validate_state("status", store.root, status)
    documents = {
        member["source_file"]: store.read(member["parsed_statement"])
        for member in session["statements"]
    }
    store.check_links()
    # Ordinary file edits do not acquire the panel lock. Reject a mixed snapshot.
    if (
        etag(store.read(store.session_path)) != etag(session)
        or load_state(checked_path(store.root, "statements/import-status.yml"))
        != status
        or any(
            etag(store.read(member["parsed_statement"]))
            != etag(documents[member["source_file"]])
            for member in session["statements"]
        )
    ):
        invalid("Review data changed during export; refresh and retry.")
    return {
        "schema_version": 1,
        "exported_at": exported_at,
        "workspace": str(store.root),
        "session": session,
        "status": {
            "version": status["version"],
            "statements": {
                source: status["statements"][source] for source in documents
            },
        },
        "documents": documents,
        "validation_current": {
            "statements": {
                source: validation_current(
                    store.root,
                    material(document),
                    document["review"].get("validation"),
                    document,
                    store,
                )
                for source, document in documents.items()
            },
            "prices": {
                run["run_id"]: validation_current(
                    store.root, price_material(run), run.get("validation")
                )
                for run in session["price_runs"]
            },
        },
        "excluded_data": [
            "Raw statement attachments",
            "Canonical ledger-file contents",
        ],
    }


def _suggestions(block: dict[str, Any]) -> str:
    result = []
    if block.get("suggestions"):
        result.append(
            "<ul>"
            + "".join(f"<li>{esc(item)}</li>" for item in block["suggestions"])
            + "</ul>"
        )
    if "answer" in block:
        result.append(paragraph("Saved answer: " + block["answer"]))
    return "".join(result)


def _accounts(document: dict[str, Any]) -> str:
    result = ["<h3>Accounts &amp; balances</h3>"]
    accounts = document["statement_metadata"]["accounts"]
    if not accounts:
        result.append(paragraph("Account evidence is not available yet.", "muted"))
    for account in accounts:
        decision = account.get("review", {})
        needs = decision.get("state") == "needs_input"
        result.append('<section class="card' + (" needs" if needs else "") + '">')
        result.append(
            "<h4>"
            + ("⚠ Needs input · " if needs else "")
            + esc(account.get("account_name", account["account_id"]))
            + "</h4>"
        )
        result.append(paragraph(f"Account ID: {account['account_id']}", "context"))
        result.append(
            paragraph(
                "Ledger mapping: " + decision.get("ledger_account", "Unavailable")
            )
        )
        if decision.get("rationale"):
            result.append(paragraph(decision["rationale"]))
        result.append(_suggestions(decision))
        result.append("<dl>")
        for name in ("opening_balance", "closing_balance", "available_balance"):
            balance = account.get(name)
            value = (
                f"{balance['amount']} {balance['currency']} · {balance['date']}"
                if balance
                else "Unavailable"
            )
            result.append(f"<dt>{readable(name)}</dt><dd>{esc(value)}</dd>")
        result.append("</dl>")
        for reconciliation in decision.get("reconciliation", []):
            result.append(details("Ledger balance and reconciliation", reconciliation))
        if decision.get("proposed_directives"):
            result.append(
                details("Proposed account directives", decision["proposed_directives"])
            )
        result.append("</section>")
    return "".join(result)


def _transactions(document: dict[str, Any]) -> str:
    records = document["extracted_records"]
    result = [f"<h3>Transactions ({len(records)})</h3>"]
    if not records:
        result.append(paragraph("Transaction evidence is not available yet.", "muted"))
    for account in document["statement_metadata"]["accounts"]:
        result.append(
            f"<h4>{esc(account.get('account_name', account['account_id']))}</h4>"
        )
        for record in records:
            if record["account_id"] != account["account_id"]:
                continue
            decision = record.get("review")
            needs = bool(
                decision
                and (
                    decision["state"] == "needs_input"
                    or decision["disposition"] == "hold"
                )
            )
            result.append('<section class="card' + (" needs" if needs else "") + '">')
            result.append(
                "<h4>"
                + ("⚠ Needs input · " if needs else "")
                + esc(record["description"])
                + "</h4>"
            )
            result.append(
                paragraph(
                    f"{record['transaction_date']} · {record['amount']} {record['currency']}"
                )
            )
            result.append(
                paragraph(
                    f"{record['record_id']} · {record['source_reference']}", "context"
                )
            )
            if decision:
                result.append(
                    paragraph(f"{decision['disposition']} · {decision['state']}")
                )
                result.append(
                    "<table><thead><tr><th>Posting account</th><th>Amount</th><th>Currency</th><th>Cost / price</th></tr></thead><tbody>"
                )
                for posting in decision["postings"]:
                    result.append(
                        "<tr>"
                        + "".join(
                            f"<td>{esc(value)}</td>"
                            for value in (
                                posting["account"],
                                posting["amount"],
                                posting["currency"],
                                " / ".join(
                                    str(posting[k])
                                    for k in ("cost", "price")
                                    if k in posting
                                ),
                            )
                        )
                        + "</tr>"
                    )
                result.append("</tbody></table>")
                if not decision["postings"]:
                    result.append(
                        paragraph(
                            "No local posting proposal. Inspect disposition and linked owner evidence.",
                            "muted",
                        )
                    )
                result.append(paragraph(decision["rationale"]))
                result.append(_suggestions(decision))
                result.append(
                    details(
                        "Findings and source links",
                        {
                            k: decision.get(k, [])
                            for k in ("findings", "linked_records")
                        },
                    )
                )
                for key in ("posting_owner", "existing_transaction"):
                    if key in decision:
                        result.append(details(readable(key), decision[key]))
            else:
                result.append(paragraph("Categorization unavailable.", "muted"))
            result.append("</section>")
    return "".join(result)


def _prices(session: dict[str, Any], freshness: dict[str, bool | None]) -> str:
    result = ['<section id="prices"><h2>Session &amp; prices</h2>']
    if not session["price_runs"]:
        result.append(paragraph("No price run available at capture.", "muted"))
    for run in session["price_runs"]:
        result.append('<section class="card">')
        result.append(
            f"<h3>{readable(run['state'])} · {esc(run['requested_date'])}</h3>"
        )
        result.append(paragraph(run["detail"]))
        result.append(
            paragraph("Required: " + (", ".join(run["required_commodities"]) or "None"))
        )
        result.append(
            paragraph("Coverage: " + (", ".join(run["coverage"]) or "None recorded"))
        )
        result.append(
            paragraph(
                f"Preflight: {run['preflight']} · {run['preflight_job_count']} jobs"
            )
        )
        result.append(details("Execution", run["execution"]))
        for field in ("approval", "validation"):
            if field in run:
                result.append(
                    details(
                        "Panel confirmation"
                        if field == "approval"
                        else (
                            "Ledger write validation"
                            if run[field]["stage"] == "written"
                            else "Review readiness validation (does not confirm ledger writes)"
                        ),
                        run[field],
                    )
                )
        if run.get("approval", {}).get("digest") != price_material(run):
            result.append(
                paragraph(
                    "No current panel confirmation. Approval can also be given in conversation.",
                    "muted",
                )
            )
        if freshness.get(run["run_id"]) is False:
            result.append(
                paragraph(
                    "Stale validation: the current ledger or reviewed price data differs from the saved result.",
                    "error",
                )
            )
        result.append(
            "<table><thead><tr><th>Commodity</th><th>Source</th><th>Requested date</th><th>Quote date</th><th>Outcome</th></tr></thead><tbody>"
        )
        for job in run["jobs"]:
            result.append(
                "<tr>"
                + "".join(
                    f"<td>{esc(job.get(k, 'Unavailable'))}</td>"
                    for k in (
                        "commodity",
                        "source",
                        "requested_date",
                        "quote_date",
                        "outcome",
                    )
                )
                + "</tr>"
            )
            if "directive" in job:
                result.append(
                    f'<tr><td colspan="5"><pre>{esc(job["directive"])}</pre></td></tr>'
                )
            if "detail" in job:
                result.append(f'<tr><td colspan="5">{esc(job["detail"])}</td></tr>')
        result.append("</tbody></table></section>")
    result.append("</section>")
    return "".join(result)


def _render(snapshot: dict[str, Any]) -> str:
    session = snapshot["session"]
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">",
        f"<title>Import review · {esc(session['session_id'])}</title><style>{CSS}</style></head><body><main>",
        '<header><div class="eyebrow">AUTO BEAN</div><h1>Import review</h1></header>',
        paragraph(
            f"Session {session['session_id']}",
            "context",
        ),
        paragraph(snapshot["workspace"], "context"),
        paragraph(
            f"Read-only snapshot captured {snapshot['exported_at']}. Includes the selected session’s financial data. No live updates, corrections or approvals are available in this file.",
            "notice",
        ),
        paragraph(
            "Raw statement attachments and full ledger-file contents are excluded. Reviewed postings and saved validation results are included.",
            "muted",
        ),
        '<nav aria-label="Snapshot sections"><a href="#prices">Session &amp; prices</a>',
    ]
    for index, member in enumerate(session["statements"]):
        parts.append(f'<a href="#statement-{index}">{esc(member["source_file"])}</a>')
    parts.append('<a href="#snapshot-data">Snapshot review data</a></nav>')
    parts.append(_prices(session, snapshot["validation_current"]["prices"]))
    for index, member in enumerate(session["statements"]):
        source = member["source_file"]
        document = snapshot["documents"][source]
        review = document["review"]
        entry = snapshot["status"]["statements"][source]
        parts.append(f'<section id="statement-{index}"><h2>{esc(source)}</h2>')
        parts.append(
            paragraph(
                f"Status: {entry['current_status']} · Updated: {entry.get('updated_at', 'Unavailable')}"
            )
        )
        parts.append(paragraph(f"Extraction: {document['extraction_state']}"))
        parts.append(details("Processing evidence and failures", review["processing"]))
        if review["processing"].get("needs_input"):
            parts.append(paragraph("⚠ Processing needs input", "notice"))
        parts.append(_suggestions(review["processing"]))
        parts.append(_accounts(document))
        parts.append(_transactions(document))
        parts.append("<h3>Approval and ledger validation</h3>")
        if "approval" in review:
            parts.append(
                details(
                    "Panel confirmation of reviewed transactions", review["approval"]
                )
            )
        else:
            parts.append(
                paragraph(
                    "No panel confirmation. Approval can also be given in conversation.",
                    "muted",
                )
            )
        if review.get("approval") and review["approval"]["digest"] != material(
            document
        ):
            parts.append(
                paragraph(
                    "The panel confirmation is stale because the reviewed data changed.",
                    "notice",
                )
            )
        if "validation" in review:
            parts.append(
                details(
                    "Ledger write validation"
                    if review["validation"]["stage"] == "written"
                    else "Review readiness validation (does not confirm ledger writes)",
                    review["validation"],
                )
            )
            if snapshot["validation_current"]["statements"][source] is False:
                parts.append(
                    paragraph(
                        "Stale validation: the current ledger or reviewed statement data differs from the saved result.",
                        "error",
                    )
                )
        else:
            parts.append(paragraph("Ledger validation is not available yet.", "muted"))
        parts.append("</section>")
    parts.append(
        '<details id="snapshot-data"><summary>Snapshot review data (JSON)</summary>'
        + pretty(snapshot)
        + "</details>"
    )
    parts.append(
        "<footer>Static export · All selected-session rows included · Canonical ledger unchanged by export</footer></main></body></html>"
    )
    return "".join(parts)


def render_review_html(root: Path, session_id: str) -> str:
    """Read one validated session consistently and return portable HTML."""
    store = ReviewFiles(root, session_id)
    with writer_lock(store.root):
        snapshot = _snapshot(store, now())
    return _render(snapshot)


def export_review_html(root: Path, session_id: str) -> dict[str, str]:
    """Save a uniquely named derived snapshot; never update import decisions."""
    store = ReviewFiles(root, session_id)
    exported_at = now()
    with writer_lock(store.root):
        snapshot = _snapshot(store, exported_at)
        content = _render(snapshot).encode("utf-8")
        filename = f"import-review-{store.session_id}-{uuid4().hex}.html"
        path = checked_path(store.root, f".auto-bean/exports/{filename}")
        atomic_write(path, content)
    return {
        "path": str(path),
        "filename": filename,
        "sha256": digest(content),
        "exported_at": exported_at,
    }
