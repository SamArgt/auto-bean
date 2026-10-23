"""Validate actual imported ledger rows and statement balances; never write a ledger."""

from __future__ import annotations

import glob
import re
from collections import Counter
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from auto_bean.common import WorkflowError, checked_path, digest, workspace
from auto_bean.review import (
    ReviewFiles,
    etag,
    account_decisions,
    material,
    now,
    price_material,
    require_ready,
    writer_lock,
)
from auto_bean.validation import (
    session_members,
    session_status,
    invalid,
    load_state,
    validate_state,
)


def financial_files(root: Path) -> dict[str, str]:
    """Discover includes without executing workspace Python or following symlinks."""
    result: dict[str, str] = {}
    queue = [checked_path(root, "ledger.beancount")]
    for path in checked_path(root, "beancount").rglob("*.beancount"):
        queue.append(checked_path(root, path.relative_to(root).as_posix()))
    while queue:
        path = queue.pop()
        relative = path.relative_to(root).as_posix()
        if relative in result:
            continue
        content = path.read_bytes()
        result[relative] = digest(content)
        for name in re.findall(
            r'^\s*include\s+"([^"\n]+)"', content.decode(), re.MULTILINE
        ):
            if Path(name).is_absolute():
                invalid("Ledger includes must be workspace-relative.")
            # Resolve lexical .., then recheck every component for symlinks.
            include = path.parent / name
            # Do not normalize a symlink away with a later '..' component.
            component = path.parent
            for part in Path(name).parts:
                component = component / part
                if component.is_symlink():
                    invalid("Ledger include traverses a symlink.")
            if ".." in include.parts:
                import os

                include = Path(os.path.normpath(include))
            if not include.is_relative_to(root):
                invalid("Ledger includes must remain inside the workspace.")
            pattern = include.relative_to(root).as_posix()
            checked_path(root, pattern)
            matches = glob.glob(str(include))
            if not matches:
                invalid("Ledger include does not resolve.")
            for match in matches:
                queue.append(
                    checked_path(root, Path(match).relative_to(root).as_posix())
                )
    return result


def _load(root: Path) -> tuple[list[Any], list[str], dict[str, str]]:
    from beancount import loader

    hashes = financial_files(root)
    entries, errors, _ = loader.load_file(str(root / "ledger.beancount"))
    if financial_files(root) != hashes:
        invalid("Ledger changed during validation; retry against stable files.")
    return list(entries), [str(e) for e in errors], hashes


def _identities(transaction: Any) -> list[tuple[str, str, str, str]]:
    identities = []
    for meta in [transaction.meta, *(p.meta or {} for p in transaction.postings)]:
        for prefix in ("", "peer_"):
            fields = tuple(
                meta.get(prefix + k)
                for k in ("source", "source_fingerprint", "account_id", "record_id")
            )
            if any(v is not None for v in fields):
                identities.append(fields)
    return identities


def _posting_key(posting: Any) -> tuple[Any, ...]:
    cost = posting.cost
    if cost is None:
        cost_key = None
    elif hasattr(cost, "number"):
        cost_key = (cost.number, cost.currency, cost.date, cost.label)
    else:
        # Fully specified CostSpec from parser; resolve absent lot-date below.
        cost_key = (cost.number_per, cost.currency, cost.date, cost.label)
        if cost.number_total is not None or cost.merge:
            invalid(
                "Review costs must use explicit per-unit lots, not total or merged costs."
            )
    units = posting.units
    if not isinstance(getattr(units, "number", None), Decimal) or not isinstance(
        getattr(units, "currency", None), str
    ):
        invalid("Review postings require explicit decimal units.")
    price = (
        (posting.price.number, posting.price.currency)
        if posting.price is not None
        else None
    )
    if cost_key and (
        not isinstance(cost_key[0], Decimal) or not isinstance(cost_key[1], str)
    ):
        invalid("Review costs require explicit decimal amounts and currencies.")
    if price and (not isinstance(price[0], Decimal) or not isinstance(price[1], str)):
        invalid("Review prices require explicit decimal amounts and currencies.")
    return (posting.account, units.number, units.currency, cost_key, price)


def _proposed_transaction(record: dict[str, Any]) -> Any:
    from beancount.core.data import Transaction
    from beancount.parser import parser

    lines = []
    for p in record["review"]["postings"]:
        # cost includes braces, price includes @ or @@, as displayed in the review.
        lines.append(
            f"  {p['account']} {p['amount']} {p['currency']} {p.get('cost', '')} {p.get('price', '')}"
        )
    text = (
        f'{record["transaction_date"]} * "Reviewed transaction"\n'
        + "\n".join(lines)
        + "\n"
    )
    entries, errors, _ = parser.parse_string(text)
    if errors or len(entries) != 1 or not isinstance(entries[0], Transaction):
        invalid("Reviewed postings do not parse as one explicit transaction.")
    return entries[0]


def expected_postings(record: dict[str, Any]) -> Counter[tuple[Any, ...]]:
    transaction = _proposed_transaction(record)
    result: Counter[tuple[Any, ...]] = Counter()
    for p in transaction.postings:
        key = _posting_key(p)
        # New acquisition lots without an explicit date receive the transaction date.
        if key[3] is not None and key[3][2] is None:
            if key[1] < 0:
                invalid("Disposal review must specify the exact cost lot date.")
            key = (
                *key[:3],
                (key[3][0], key[3][1], transaction.date, key[3][3]),
                key[4],
            )
        result[key] += 1
    return result


def _require_balanced(keys: Counter[tuple[Any, ...]]) -> None:
    totals: dict[str, Decimal] = {}
    for key, count in keys.items():
        _, units, currency, cost, price = key
        if cost:
            units, currency = units * cost[0], cost[1]
        elif price:
            units, currency = units * price[0], price[1]
        totals[currency] = totals.get(currency, Decimal(0)) + units * count
    if any(totals.values()):
        invalid("Reviewed postings do not balance by commodity weight.")


def _match(record: dict[str, Any], doc: dict[str, Any], transaction: Any) -> None:
    if transaction.date.isoformat() != record["transaction_date"]:
        invalid(
            f"{record['record_id']}: ledger date differs from reviewed transaction."
        )
    if record.get("payee") and transaction.payee != record["payee"]:
        invalid(f"{record['record_id']}: ledger payee differs from source evidence.")
    if (
        record["review"]["disposition"] != "existing_duplicate"
        and transaction.narration != record["description"]
    ):
        invalid(
            f"{record['record_id']}: ledger narration differs from source description."
        )
    expected = expected_postings(record)
    actual = Counter(_posting_key(p) for p in transaction.postings)
    if actual != expected:
        invalid(
            f"{record['record_id']}: ledger postings differ from reviewed postings."
        )
    mapping = account_decisions(doc)[record["account_id"]]["ledger_account"]
    amount = sum(
        (
            p.units.number
            for p in transaction.postings
            if p.account == mapping
            and p.units is not None
            and p.units.currency == record["currency"]
            and isinstance(p.units.number, Decimal)
        ),
        Decimal(0),
    )
    if amount != Decimal(record["amount"]):
        invalid(
            f"{record['record_id']}: ledger movement differs from the extracted amount/account/currency."
        )


def check_directives(
    root: Path, document: dict[str, Any], entries: list[Any], errors: list[str]
) -> None:
    """Required approved supporting directives must exist in the actual include graph."""
    from beancount.core.data import Open, Balance, Document, Transaction
    from beancount.parser import parser

    for account in document["statement_metadata"]["accounts"]:
        for text in account["review"].get("proposed_directives", []):
            proposed, problems, options = parser.parse_string(
                text + "\n", report_filename=str(root / "ledger.beancount")
            )
            if (
                problems
                or not proposed
                or options.get("include")
                or options.get("plugin")
            ):
                errors.append(
                    "Supporting directives must parse without includes or plugins."
                )
                continue
            for expected in proposed:
                matched = False
                for actual in entries:
                    if (
                        type(actual) is not type(expected)
                        or actual.date != expected.date
                    ):
                        continue
                    if isinstance(expected, Open):
                        matched = (
                            actual.account == expected.account
                            and actual.currencies == expected.currencies
                            and actual.booking == expected.booking
                        )
                    elif isinstance(expected, Balance):
                        matched = (
                            actual.account == expected.account
                            and actual.amount == expected.amount
                            and actual.tolerance == expected.tolerance
                        )
                    elif isinstance(expected, Document):
                        target = Path(expected.filename)
                        if not target.is_absolute():
                            target = root / target
                        if target.is_relative_to(root):
                            target = checked_path(
                                root, target.relative_to(root).as_posix()
                            )
                            matched = (
                                actual.account == expected.account
                                and Path(actual.filename) == target
                                and target.is_file()
                            )
                        else:
                            invalid(
                                "Document directives must stay within the selected workspace."
                            )
                    elif isinstance(expected, Transaction):
                        try:
                            wanted = Counter(_posting_key(p) for p in expected.postings)
                            matched = (
                                actual.payee == expected.payee
                                and actual.narration == expected.narration
                                and Counter(_posting_key(p) for p in actual.postings)
                                == wanted
                            )
                        except WorkflowError:
                            matched = False
                    if matched:
                        break
                if not matched:
                    errors.append(
                        f"{account['account_id']}: approved supporting directive missing or different: {text}"
                    )


def _inspect_statement(
    store: ReviewFiles, source: str, stage: str = "written"
) -> dict[str, Any]:
    """Compute a fresh report; caller holds the workspace lock when publishing."""
    from beancount.core.data import Transaction

    doc = store.statement(source)
    result: dict[str, Any] = {
        "state": "failed",
        "stage": stage,
        "checked_at": now(),
        "digest": material(doc),
        "ledger_hashes": {},
        "records_checked": 0,
        "balances": [],
        "errors": [],
    }
    errors = result["errors"]
    try:
        require_ready(doc)
        store.check_links([source])
        if (
            "sha256:" + digest(checked_path(store.root, source).read_bytes())
            != doc["source_fingerprint"]
        ):
            invalid("Source bytes no longer match extracted evidence.")
        entries, ledger_errors, hashes = _load(store.root)
        result["ledger_hashes"] = hashes
        errors.extend(ledger_errors)
        if stage == "review":
            _check_proposals(store, doc, entries, result)
            if financial_files(store.root) != hashes:
                errors.append("Ledger changed during review validation.")
            result["state"] = "passed" if not errors else "failed"
            return result
        transactions = [e for e in entries if isinstance(e, Transaction)]
        allowed = {(r["account_id"], r["record_id"]) for r in doc["extracted_records"]}
        for tx in transactions:
            for identity in _identities(tx):
                if identity[0] == source and (
                    identity[1] != doc["source_fingerprint"]
                    or identity[2:] not in allowed
                ):
                    errors.append(
                        "Ledger contains unknown or changed source-row provenance."
                    )
        used: dict[int, dict[str, Any]] = {}
        for row in doc["extracted_records"]:
            try:
                decision = row["review"]
                identity = (
                    source,
                    doc["source_fingerprint"],
                    row["account_id"],
                    row["record_id"],
                )
                matches = [tx for tx in transactions if identity in _identities(tx)]
                if decision["disposition"] == "existing_duplicate":
                    ref = decision["existing_transaction"]
                    path = checked_path(store.root, ref["path"])
                    referenced = [
                        tx
                        for tx in transactions
                        if Path(tx.meta["filename"]) == path
                        and tx.meta["lineno"] == ref["line"]
                    ]
                    if matches and (len(matches) != 1 or matches != referenced):
                        invalid(f"{row['record_id']}: duplicate row was also posted.")
                    matches = referenced
                if len(matches) != 1:
                    invalid(
                        f"{row['record_id']}: expected exactly one ledger transaction, found {len(matches)}."
                    )
                tx = matches[0]
                other = used.get(id(tx))
                if other is not None and not (
                    decision["disposition"]
                    == other["review"]["disposition"]
                    == "paired_transfer"
                ):
                    invalid(
                        "Distinct source rows cannot silently share one transaction."
                    )
                used[id(tx)] = row
                if decision["disposition"] == "paired_transfer":
                    if len(decision["linked_records"]) != 1:
                        invalid(
                            "A paired transfer requires exactly two reciprocal source rows."
                        )
                    link = decision["linked_records"][0]
                    peer_doc = store.statement(link["source_file"])
                    require_ready(peer_doc)
                    if (
                        "sha256:"
                        + digest(
                            checked_path(store.root, link["source_file"]).read_bytes()
                        )
                        != peer_doc["source_fingerprint"]
                    ):
                        invalid("Linked source bytes changed.")
                    peer = next(
                        r
                        for r in peer_doc["extracted_records"]
                        if r["record_id"] == link["record_id"]
                        and r["account_id"] == link["account_id"]
                    )
                    peer_identity = (
                        link["source_file"],
                        peer_doc["source_fingerprint"],
                        link["account_id"],
                        link["record_id"],
                    )
                    if peer_identity not in _identities(tx):
                        invalid("Paired transfer lost its peer provenance.")
                    if set(_identities(tx)) != {identity, peer_identity}:
                        invalid(
                            "A paired transfer must cover exactly its two linked source rows."
                        )
                    if (
                        len(
                            [t for t in transactions if peer_identity in _identities(t)]
                        )
                        != 1
                    ):
                        invalid("Paired transfer was posted more than once.")
                    # Both rows approve the full transaction; empty non-owner postings
                    # borrow the explicitly linked owner's reviewed postings.
                    if source == link["source_file"]:
                        owner = min((row, peer), key=lambda r: r["record_id"])
                    else:
                        owner = row if source == decision["posting_owner"] else peer
                    if not owner["review"]["postings"]:
                        invalid("Transfer posting owner has no reviewed postings.")
                    matching_row = {
                        **row,
                        "transaction_date": owner["transaction_date"],
                        "description": owner["description"],
                        "payee": owner.get("payee"),
                        "review": {**decision, "postings": owner["review"]["postings"]},
                    }
                    _match(matching_row, doc, tx)
                    if decision["postings"] and expected_postings(
                        row
                    ) != expected_postings(owner):
                        invalid(
                            "Transfer counterpart postings disagree with the owner."
                        )
                else:
                    if decision["disposition"] == "post" and set(_identities(tx)) != {
                        identity
                    }:
                        invalid(
                            "A regular transaction must cover only its own source row."
                        )
                    _match(row, doc, tx)
                result["records_checked"] += 1
            except (WorkflowError, ValueError, StopIteration) as error:
                errors.append(str(error))
        check_directives(store.root, doc, entries, errors)
        for account in doc["statement_metadata"]["accounts"]:
            closing = account.get("closing_balance")
            if not isinstance(closing, dict):
                continue
            ledger_account = account["review"]["ledger_account"]
            end = date.fromisoformat(closing["date"])
            actual = sum(
                (
                    p.units.number
                    for tx in transactions
                    if tx.date <= end
                    for p in tx.postings
                    if p.account == ledger_account
                    and p.units is not None
                    and p.units.currency == closing["currency"]
                    and isinstance(p.units.number, Decimal)
                ),
                Decimal(0),
            )
            state = "matched" if actual == Decimal(closing["amount"]) else "mismatch"
            result["balances"].append(
                {
                    "account_id": account["account_id"],
                    "date": closing["date"],
                    "currency": closing["currency"],
                    "expected": closing["amount"],
                    "actual": str(actual),
                    "state": state,
                }
            )
            if state == "mismatch":
                errors.append(
                    f"{account['account_id']}: closing balance mismatch ({actual} vs {closing['amount']} {closing['currency']})."
                )
        if financial_files(store.root) != hashes:
            errors.append("Ledger changed during reconciliation; retry validation.")
    except (WorkflowError, OSError, ValueError) as error:
        errors.append(str(error))
    if not errors:
        result["state"] = "passed"
    return result


def stable_report(
    previous: dict[str, Any] | None, current: dict[str, Any]
) -> dict[str, Any]:
    """Keep audit timestamps on a fresh identical recheck; changed inputs get new evidence."""
    if previous and {k: v for k, v in previous.items() if k != "checked_at"} == {
        k: v for k, v in current.items() if k != "checked_at"
    }:
        return previous
    return current


def _validate_statement(
    store: ReviewFiles, source: str, stage: str = "written"
) -> dict[str, Any]:
    with writer_lock(store.root):
        doc = store.statement(source)
        token = etag(doc)
        stage = validation_stage(stage, doc["review"].get("validation"), material(doc))
        result = _inspect_statement(store, source, stage)
        result = stable_report(doc["review"].get("validation"), result)
        if etag(store.statement(source)) != token:
            invalid("Parsed evidence changed during validation; retry.")
        if (
            "sha256:" + digest(checked_path(store.root, source).read_bytes())
            != doc["source_fingerprint"]
        ):
            result["state"] = "failed"
            result["errors"].append(
                "Source changed during validation; recheck extraction."
            )
        if doc["review"].get("validation") != result:
            doc["review"]["validation"] = result
            store._publish_statement(source, doc, token)
        return result


def validation_stage(
    requested: str, previous: dict[str, Any] | None, evidence_digest: str
) -> str:
    """Recheck completed evidence instead of downgrading it to proposal checks."""
    if (
        requested == "review"
        and previous
        and previous.get("stage") == "written"
        and previous.get("state") == "passed"
        and previous.get("digest") == evidence_digest
    ):
        return "written"
    return requested


def _validate_prices(
    store: ReviewFiles, run_id: str, stage: str = "written"
) -> dict[str, Any]:
    from beancount.core.data import Price
    from beancount.parser import parser

    with writer_lock(store.root):
        session = store.read(store.session_path)
        token = etag(session)
        run = next((r for r in session["price_runs"] if r["run_id"] == run_id), None)
        if run is None:
            invalid("Unknown price run.")
        stage = validation_stage(stage, run.get("validation"), price_material(run))
        result: dict[str, Any] = {
            "state": "failed",
            "stage": stage,
            "checked_at": now(),
            "digest": price_material(run),
            "ledger_hashes": {},
            "records_checked": 0,
            "balances": [],
            "errors": [],
        }
        try:
            entries, errors, hashes = _load(store.root)
            result["ledger_hashes"] = hashes
            result["errors"].extend(errors)
            if run["state"] not in {"complete", "no_op"}:
                result["errors"].append("Price run has unresolved jobs.")
            for job in run["jobs"]:
                if job["outcome"] not in {"emitted", "redundant"}:
                    continue
                proposed, problems, _ = parser.parse_string(job.get("directive", ""))
                if problems or len(proposed) != 1 or not isinstance(proposed[0], Price):
                    invalid("Price result must identify its exact directive.")
                expected = proposed[0]
                if (
                    expected.currency != job["commodity"]
                    or expected.date.isoformat() != job["quote_date"]
                ):
                    invalid("Price directive disagrees with its source result.")
                matches = [
                    e
                    for e in entries
                    if isinstance(e, Price)
                    and e.date == expected.date
                    and e.currency == expected.currency
                    and e.amount == expected.amount
                ]
                if stage == "written" and len(matches) != 1:
                    result["errors"].append(
                        f"{job['commodity']}: expected exactly one matching price directive."
                    )
                else:
                    result["records_checked"] += 1
            if financial_files(store.root) != hashes:
                invalid("Ledger changed during price validation.")
        except (WorkflowError, OSError, ValueError) as error:
            result["errors"].append(str(error))
        if not result["errors"]:
            result["state"] = "passed"
        result = stable_report(run.get("validation"), result)
        if etag(store.read(store.session_path)) != token:
            invalid("Price results changed during validation; retry.")
        if run.get("validation") != result:
            run["validation"] = result
            store._publish(store.session_path, session, token)
        return result


def _check_proposals(
    store: ReviewFiles, doc: dict[str, Any], entries: list[Any], report: dict[str, Any]
) -> None:
    """Validate proposed economics without constructing files or requiring prior writes."""
    from beancount.core.data import Transaction, Open, Balance, Document, entry_sortkey
    from beancount.ops import validation
    from beancount.parser import parser

    account_entries = list(entries)
    # Shared transfers can use an account whose opening belongs to another member.
    for member in session_members(store.read(store.session_path)):
        other = store.statement(member["source_file"])
        for account in other["statement_metadata"]["accounts"]:
            for text in account.get("review", {}).get("proposed_directives", []):
                proposed, problems, _ = parser.parse_string(text + "\n")
                if problems:
                    continue  # The owning statement reports its invalid directive.
                for entry in proposed:
                    if isinstance(entry, Open) and not any(
                        isinstance(existing, Open)
                        and entry._replace(meta={}) == existing._replace(meta={})
                        for existing in account_entries
                    ):
                        account_entries.append(entry)
    for account in doc["statement_metadata"]["accounts"]:
        for text in account["review"].get("proposed_directives", []):
            proposed, problems, options = parser.parse_string(
                text + "\n", report_filename=str(store.root / "ledger.beancount")
            )
            if (
                problems
                or not proposed
                or options.get("include")
                or options.get("plugin")
                or any(
                    not isinstance(e, (Transaction, Open, Balance, Document))
                    for e in proposed
                )
            ):
                report["errors"].append(
                    f"{account['account_id']}: invalid supporting directive."
                )
            else:
                for entry in proposed:
                    if isinstance(entry, Open):
                        continue
                    try:
                        if isinstance(entry, Transaction):
                            _require_balanced(
                                Counter(_posting_key(p) for p in entry.postings)
                            )
                        account_entries.append(entry)
                    except WorkflowError as error:
                        report["errors"].append(f"{account['account_id']}: {error}")
    for row in doc["extracted_records"]:
        try:
            decision = row["review"]
            owner = row
            if decision["disposition"] == "paired_transfer":
                if len(decision["linked_records"]) != 1:
                    invalid(
                        "A paired transfer requires exactly two reciprocal source rows."
                    )
                link = decision["linked_records"][0]
                peer_doc = store.statement(link["source_file"])
                require_ready(peer_doc)
                peer = next(
                    r
                    for r in peer_doc["extracted_records"]
                    if r["record_id"] == link["record_id"]
                )
                owner = (
                    min((row, peer), key=lambda r: r["record_id"])
                    if doc["source_file"] == link["source_file"]
                    else row
                    if decision["posting_owner"] == doc["source_file"]
                    else peer
                )
            keys = expected_postings(owner)
            if not keys:
                invalid("A reviewed transaction needs explicit postings.")
            if decision["postings"] and expected_postings(row) != keys:
                invalid("Transfer counterpart postings disagree with the owner.")
            _require_balanced(keys)
            account = account_decisions(doc)[row["account_id"]]["ledger_account"]
            movement = sum(
                (
                    key[1] * count
                    for key, count in keys.items()
                    if key[0] == account and key[2] == row["currency"]
                ),
                Decimal(0),
            )
            if movement != Decimal(row["amount"]):
                invalid(
                    "Reviewed postings do not match the extracted account movement."
                )
            if decision["disposition"] == "existing_duplicate":
                ref = decision["existing_transaction"]
                existing = [
                    tx
                    for tx in entries
                    if isinstance(tx, Transaction)
                    and Path(tx.meta["filename"])
                    == checked_path(store.root, ref["path"])
                    and tx.meta["lineno"] == ref["line"]
                ]
                if len(existing) != 1:
                    invalid(
                        "Reviewed duplicate does not identify one canonical transaction."
                    )
                _match(row, doc, existing[0])
            account_entries.append(_proposed_transaction(owner))
            report["records_checked"] += 1
        except (WorkflowError, ValueError, StopIteration) as error:
            report["errors"].append(f"{row['record_id']}: {error}")
    account_entries.sort(key=entry_sortkey)
    checks: tuple[Callable[[list[Any], dict[str, Any]], list[Any]], ...] = (
        validation.validate_open_close,
        validation.validate_active_accounts,
        validation.validate_currency_constraints,
    )
    for check in checks:
        report["errors"].extend(str(error) for error in check(account_entries, {}))


def validate_import(
    root: Path,
    session_id: str | None = None,
    stage: str = "written",
    *,
    price_run_id: str | None = None,
) -> dict[str, Any]:
    """The single validation operation. Financial correctness never grants approval."""
    result: dict[str, Any] = {
        "state": "failed",
        "stage": stage,
        "statements": {},
        "prices": {},
        "groups": {},
        "errors": [],
    }
    try:
        if stage not in {"review", "written"}:
            invalid("Validation stage must be review or written.")
        if price_run_id is not None and not session_id:
            invalid("Price-run validation requires a session.")
        root = workspace(root)
        status = load_state(checked_path(root, "statements/import-status.yml"))
        validate_state("status", root, status)
        if session_id is None:
            _, errors, hashes = _load(root)
            result["errors"].extend(errors)
            result["ledger_hashes"] = hashes
            for path in checked_path(root, ".auto-bean/memory").rglob("*.json"):
                safe = checked_path(root, path.relative_to(root).as_posix())
                try:
                    validate_state("memory", root, load_state(safe))
                except (WorkflowError, OSError, ValueError) as error:
                    result["errors"].append(f"{path.relative_to(root)}: {error}")
        else:
            files = ReviewFiles(root, session_id)
            session = files.read(files.session_path)
            session_status(session, status)
            result["session_id"] = session_id
            price_runs = session["price_runs"]
            if price_run_id is not None:
                price_runs = [r for r in price_runs if r["run_id"] == price_run_id]
                if len(price_runs) != 1:
                    invalid("Selected price run does not exist in the session.")
            for item in [] if price_run_id is not None else session_members(session):
                source = item["source_file"]
                try:
                    source_stage = (
                        "written"
                        if status["groups"][item["group_id"]]["current_status"]
                        == "done"
                        else stage
                    )
                    report = _validate_statement(files, source, source_stage)
                    result["statements"][source] = report
                    result["errors"].extend(
                        f"{source}: {error}" for error in report["errors"]
                    )
                except (WorkflowError, OSError, ValueError) as error:
                    result["errors"].append(f"{source}: {error}")
            for group in [] if price_run_id is not None else session["groups"]:
                reports = [
                    result["statements"].get(source) for source in group["source_files"]
                ]
                passed = all(
                    report and report["state"] == "passed" for report in reports
                )
                result["groups"][group["group_id"]] = {
                    "state": "passed" if passed else "failed",
                    "stage": "written"
                    if all(
                        report and report["stage"] == "written" for report in reports
                    )
                    else stage,
                    "source_files": group["source_files"],
                }
                if status["groups"][group["group_id"]]["current_status"] == "done" and (
                    not passed
                ):
                    result["errors"].append(
                        f"{group['group_id']}: done requires written validation for every member."
                    )
            for run in price_runs:
                try:
                    report = _validate_prices(files, run["run_id"], stage)
                    result["prices"][run["run_id"]] = report
                    result["errors"].extend(
                        f"{run['run_id']}: {error}" for error in report["errors"]
                    )
                except (WorkflowError, OSError, ValueError) as error:
                    result["errors"].append(f"{run['run_id']}: {error}")
            # Direct edits do not participate in the panel lock. Check the whole
            # session again so sequential checks cannot report a mixed baseline.
            current = files.read(files.session_path)
            if load_state(checked_path(root, "statements/import-status.yml")) != status:
                invalid("Group status changed during validation; retry.")
            if current["groups"] != session["groups"] or [
                price_material(r) for r in current["price_runs"]
            ] != [price_material(r) for r in session["price_runs"]]:
                invalid(
                    "Session changed during validation; retry against stable files."
                )
            hashes = financial_files(root)
            for source, report in result["statements"].items():
                doc = files.statement(source)
                if report["state"] == "passed" and (
                    report["digest"] != material(doc)
                    or report["ledger_hashes"] != hashes
                    or "sha256:" + digest(checked_path(root, source).read_bytes())
                    != doc["source_fingerprint"]
                ):
                    invalid("Statement or ledger changed during validation; retry.")
            if any(
                report["state"] == "passed" and report["ledger_hashes"] != hashes
                for report in result["prices"].values()
            ):
                invalid("Ledger changed during validation; retry.")
    except (WorkflowError, OSError, ValueError) as error:
        result["errors"].append(str(error))
    if not result["errors"]:
        result["state"] = "passed"
    return result


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate Auto Bean artifacts and ledger results; does not authorize writes."
    )
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--session")
    parser.add_argument("--price-run")
    parser.add_argument("--stage", choices=("review", "written"), default="written")
    args = parser.parse_args()
    result = validate_import(
        args.workspace, args.session, args.stage, price_run_id=args.price_run
    )
    print(json.dumps(result, indent=2))
    return 0 if result["state"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
