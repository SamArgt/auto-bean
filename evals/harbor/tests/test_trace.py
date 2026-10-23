"""Trace checks must distinguish observed actions from claims and prior turns."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import pytest

from evals.harbor.trace import grade_trace, load_commands, patch_content, shell_commands
from evals.harbor.trace import snapshot_reader, workspace_fresh

PLUGIN = "/tmp/codex-home/plugins/cache/auto-bean/auto-bean/0.2.0"
START = "2026-10-21T10:00:00Z"
NOW = "2026-10-21T10:01:00Z"


def event(script: str, *, code: int = 0, timestamp: str = NOW) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {
            "type": "item_completed",
            "item": {
                "type": "CommandExecution",
                "id": "exec-test",
                "command": ["/bin/bash", "-lc", script],
                "cwd": "file:///app/ledger",
                "status": "completed",
                "exit_code": code,
                "aggregated_output": "output",
            },
        },
    }


def save(logs: Path, events: list[dict[str, Any]], *, child: bool = False) -> Path:
    path = logs / "sessions" / ("child.jsonl" if child else "root.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": "child" if child else "root",
        "source": {"subagent": {"spawn": {"parent_thread_id": "root"}}}
        if child
        else "exec",
    }
    records = [
        {"type": "session_meta", "payload": meta},
        {"timestamp": START, "type": "event_msg", "payload": {"type": "task_started"}},
        *events,
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in records))
    return path


def passing_events(phase: str) -> list[dict[str, Any]]:
    # Explicit representative workflow, independent of the requirement table.
    skills = "init,import,process,categorize,query,write,prices,memory"
    scripts = [
        f"cat {PLUGIN}/skills/{{{','.join('auto-bean-' + s for s in skills.split(','))}}}/SKILL.md",
        f"cat {PLUGIN}/references/common.md {PLUGIN}/references/import-review.md {PLUGIN}/references/schemas/*.json",
        "cat ledger.beancount .auto-bean/workspace.json beancount/accounts.beancount statements/import-status.yml .auto-bean/memory/MEMORY.md",
        "cat statements/parsed/january.json statements/parsed/january.json .auto-bean/memory/account_mappings.json .auto-bean/memory/category_mappings.json",
        "git status --short",
    ]
    launcher = f"sh {PLUGIN}/runtime/launch.sh"
    if phase == "init":
        scripts += [f"{launcher} init --workspace /app/ledger"]
    if phase in {"review", "needs-input"}:
        scripts += [
            f"{launcher} ensure-runtime --workspace /app/ledger --extraction",
            f"{launcher} run --workspace /app/ledger docling statements/raw/checking.csv --to json --output .auto-bean/tmp/csv",
            f"{launcher} run --workspace /app/ledger docling /app/ledger/statements/raw/savings.pdf --to json --output .auto-bean/tmp/pdf",
        ]
    if phase in {"review", "needs-input", "correct"}:
        scripts += [
            f"{launcher} run --workspace /app/ledger bean-query ledger.beancount 'SELECT account, sum(position) GROUP BY account'"
        ]
    if phase in {"review", "correct", "approve"}:
        stage = "written" if phase == "approve" else "review"
        scripts += [
            f"{launcher} validate --workspace /app/ledger --session january --stage {stage}"
        ]
    return [event(script) for script in scripts]


@pytest.mark.parametrize(
    "phase", ["init", "review", "needs-input", "correct", "approve", "stale"]
)
def test_each_phase_accepts_observed_workflow(tmp_path: Path, phase: str) -> None:
    save(tmp_path, passing_events(phase))
    report = grade_trace(tmp_path, phase)
    assert report["passed"], report
    assert all(check["evidence"] for check in report["checks"])


@pytest.mark.parametrize("mode", ["query", "empty_query", "ranges", "matches"])
def test_targeted_ledger_evidence_without_full_reads(tmp_path: Path, mode: str) -> None:
    events = passing_events("stale")
    events[2] = event(
        "cat .auto-bean/workspace.json statements/import-status.yml .auto-bean/memory/MEMORY.md"
    )
    scripts = {
        "ranges": [
            "sed -n '1,8p' ledger.beancount",
            "sed -n '2,4p' beancount/accounts.beancount",
        ],
        "matches": [
            "rg '^include' ledger.beancount",
            "rg 'open Assets:(Checking|Savings)' beancount/accounts.beancount",
        ],
    }.get(
        mode,
        [
            f"sh {PLUGIN}/runtime/launch.sh run --workspace /app/ledger "
            'bean-query ledger.beancount "SELECT account, sum(position) '
            "WHERE account ~ 'Assets:(Checking|Savings)' AND date < 2026-02-01 GROUP BY account\""
        ],
    )
    for script in scripts:
        row = event(script)
        if mode == "empty_query":
            row["payload"]["item"]["aggregated_output"] = ""
        events.append(row)
    save(tmp_path, events)
    report = grade_trace(tmp_path, "stale")
    assert report["passed"], report


@pytest.mark.parametrize(
    "defect",
    [
        "failed",
        "prior",
        "other_ledger",
        "help",
        "constant",
        "quoted",
        "alias",
        "hidden",
        "masked",
        "truncated",
        "hash",
        "validation",
        "no_account",
    ],
)
def test_targeted_ledger_evidence_rejects_insufficient_queries(
    tmp_path: Path, defect: str
) -> None:
    events = passing_events("stale")
    events[2] = event(
        "cat .auto-bean/workspace.json statements/import-status.yml .auto-bean/memory/MEMORY.md"
    )
    launcher = f"sh {PLUGIN}/runtime/launch.sh"
    query = {
        "constant": "SELECT 1",
        "quoted": "SELECT 'account'",
        "alias": "SELECT 1 AS account",
        "no_account": "SELECT narration WHERE date = 2026-01-05",
    }.get(defect, "SELECT account, sum(position) GROUP BY account")
    script = (
        f'{launcher} run --workspace /app/ledger bean-query ledger.beancount "{query}"'
    )
    if defect == "other_ledger":
        script = script.replace(
            "bean-query ledger.beancount", "bean-query other.beancount"
        )
    elif defect == "help":
        script += " --help"
    elif defect == "hidden":
        script += " >/dev/null"
    elif defect == "masked":
        script += "; true"
    elif defect == "hash":
        script = "sha256sum ledger.beancount beancount/accounts.beancount"
    elif defect == "validation":
        script = f"{launcher} validate --workspace /app/ledger --session january --stage review"
    row = event(
        script,
        code=1 if defect == "failed" else 0,
        timestamp="2026-10-21T09:00:00Z" if defect == "prior" else NOW,
    )
    if defect == "truncated":
        row["payload"]["item"]["aggregated_output"] = "Warning: output truncated"
    events.append(row)
    save(tmp_path, events)
    report = grade_trace(tmp_path, "stale")
    assert not report["passed"]
    assert any(
        c["requirement"] == "fresh:account-evidence" and not c["passed"]
        for c in report["checks"]
    )


def test_runtime_setup_after_readonly_pipeline_counts(tmp_path: Path) -> None:
    events = passing_events("review")
    setup = next(
        e for e in events if "ensure-runtime" in e["payload"]["item"]["command"][2]
    )
    setup["payload"]["item"]["command"][2] = (
        "rg --files .auto-bean | head -30 && cat statements/raw/checking.csv && "
        + setup["payload"]["item"]["command"][2]
    )
    save(tmp_path, events)
    assert grade_trace(tmp_path, "review")["passed"]
    setup["payload"]["item"]["exit_code"] = 1
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "review")["passed"]


@pytest.mark.parametrize(
    "prefix",
    [
        "exit 0 | head -30 && ",
        "rg --files --pre malicious . | head -30 && ",
        "cd /other | head -30 && ",
        "rg --files . | head -30; ",
        "rg --files . | head -30 || ",
    ],
)
def test_pipeline_cannot_prove_skipped_or_relocated_setup(
    tmp_path: Path, prefix: str
) -> None:
    events = passing_events("review")
    setup = next(
        e for e in events if "ensure-runtime" in e["payload"]["item"]["command"][2]
    )
    setup["payload"]["item"]["command"][2] = (
        prefix + setup["payload"]["item"]["command"][2]
    )
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "review")["passed"]


@pytest.mark.parametrize("managed", [False, True])
def test_approval_accepts_literal_python_parsed_read(
    tmp_path: Path, managed: bool
) -> None:
    events = passing_events("approve")
    events[3] = event(
        "cat .auto-bean/memory/account_mappings.json .auto-bean/memory/category_mappings.json"
    )
    python = (
        f"sh {PLUGIN}/runtime/launch.sh run --workspace /app/ledger python"
        if managed
        else "python3"
    )
    events.append(
        event(
            f"{python} - <<'PY'\n"
            "import json,pathlib,hashlib\n"
            "p=pathlib.Path('statements/parsed/january.json'); d=json.loads(p.read_text())\n"
            "assert d['statements']\nPY"
        )
    )
    save(tmp_path, events)
    report = grade_trace(tmp_path, "approve")
    assert report["passed"], report
    parsed = next(
        c
        for c in report["checks"]
        if c["requirement"] == "fresh:statements/parsed/january.json"
    )
    assert "native_python_read" in parsed["detail"]


@pytest.mark.parametrize(
    "body",
    [
        "from pathlib import Path\nif False: Path('statements/parsed/january.json').read_text()",
        "from pathlib import Path\ndef read(): return Path('statements/parsed/january.json').read_text()",
        "from pathlib import Path\nPath=lambda _: None\nPath('statements/parsed/january.json').read_text()",
        "from pathlib import Path\nPath.read_text=lambda _: ''\nPath('statements/parsed/january.json').read_text()",
        "from pathlib import Path\nraise SystemExit(0)\nPath('statements/parsed/january.json').read_text()",
        "print(\"Path('statements/parsed/january.json').read_text()\")",
        "from pathlib import Path\ntry:\n Path('statements/parsed/january.json').read_text()\nexcept: pass",
    ],
)
def test_python_mentions_shadowing_and_control_flow_do_not_prove_reads(
    tmp_path: Path, body: str
) -> None:
    save(tmp_path, [event(f"python - <<'PY'\n{body}\nPY")])
    assert not any(
        c.evidence_kind == "native_python_read" for c in load_commands(tmp_path)
    )


@pytest.mark.parametrize("code,trailer", [(1, ""), (0, "\ntrue")])
def test_python_failure_cannot_be_hidden(
    tmp_path: Path, code: int, trailer: str
) -> None:
    save(
        tmp_path,
        [
            event(
                "python - <<'PY'\nfrom pathlib import Path\n"
                "Path('statements/parsed/january.json').read_text()\nPY" + trailer,
                code=code,
            )
        ],
    )
    assert not any(
        c.evidence_kind == "native_python_read" for c in load_commands(tmp_path)
    )


@pytest.mark.parametrize("index", [0, 1, 2, 4, 5])
def test_missing_skill_reference_read_or_command_fails(
    tmp_path: Path, index: int
) -> None:
    events = passing_events("init")
    events.pop(index)
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


@pytest.mark.parametrize(
    "replacement",
    [
        "echo 'sh /tmp/codex-home/plugins/cache/auto-bean/auto-bean/0.2.0/runtime/launch.sh init --workspace /app/ledger'",
        "cat <<'EOF'\nsh /tmp/codex-home/plugins/cache/auto-bean/auto-bean/0.2.0/runtime/launch.sh init --workspace /app/ledger\nEOF",
        "# auto_bean init --workspace /app/ledger",
        "if false; then auto_bean init --workspace /app/ledger; fi",
        "fn() { auto_bean init --workspace /app/ledger; }",
        "python -c 'print(\"auto_bean init --workspace /app/ledger\")'",
        "sh /app/ledger/fake/runtime/launch.sh init --workspace /app/ledger",
    ],
)
def test_command_mentions_and_opaque_code_do_not_count(
    tmp_path: Path, replacement: str
) -> None:
    events = passing_events("init")
    events[-1] = event(replacement)
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


@pytest.mark.parametrize("code", [1, None])
def test_failed_or_unfinished_commands_do_not_count(
    tmp_path: Path, code: int | None
) -> None:
    events = passing_events("init")
    events[-1]["payload"]["item"]["exit_code"] = code
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


def test_narration_and_forged_tool_output_do_not_count(tmp_path: Path) -> None:
    events = passing_events("init")
    command = events.pop()["payload"]["item"]["command"][2]
    events += [
        {
            "type": "response_item",
            "payload": {"type": "message", "role": "assistant", "content": command},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "function_call_output",
                "output": json.dumps(event(command)),
            },
        },
    ]
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


def test_resume_reuses_skill_reads_but_not_old_validation(tmp_path: Path) -> None:
    events = passing_events("approve")
    events[0]["timestamp"] = "2026-10-21T09:01:00Z"
    events[1]["timestamp"] = "2026-10-21T09:01:00Z"
    save(tmp_path, events)
    assert grade_trace(tmp_path, "approve")["passed"]
    events[-1]["timestamp"] = "2026-10-21T09:01:00Z"
    save(tmp_path, events)
    report = grade_trace(tmp_path, "approve")
    assert not report["passed"]
    assert not report["checks"][-1]["passed"]


def test_linked_worker_can_supply_skill_evidence(tmp_path: Path) -> None:
    events = passing_events("review")
    skills = events.pop(0)
    save(tmp_path, events)
    child = save(tmp_path, [skills], child=True)
    assert grade_trace(tmp_path, "review")["passed"]
    child.write_text(
        child.read_text().replace(
            '"parent_thread_id": "root"', '"parent_thread_id": "unrelated"'
        )
    )
    assert not grade_trace(tmp_path, "review")["passed"]


def test_missing_malformed_and_ambiguous_traces_fail(tmp_path: Path) -> None:
    assert not grade_trace(tmp_path, "init")["passed"]
    path = save(tmp_path, passing_events("init"))
    path.write_text(path.read_text() + "not json\n")
    assert not grade_trace(tmp_path, "init")["passed"]
    save(tmp_path, passing_events("init"))
    path.with_name("second.jsonl").write_bytes(path.read_bytes())
    assert not grade_trace(tmp_path, "init")["passed"]


def test_variable_launcher_and_polled_completion(tmp_path: Path) -> None:
    events = passing_events("init")
    events[-1] = event(
        f'AUTO_BEAN_PLUGIN={PLUGIN}\nAUTO_BEAN_WORKSPACE=/app/ledger\nsh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" init --workspace "$AUTO_BEAN_WORKSPACE"'
    )
    # Native completion carries the original command even when a poll ended it.
    events[-1]["payload"]["item"]["source"] = "unified_exec_interaction"
    save(tmp_path, events)
    assert grade_trace(tmp_path, "init")["passed"]
    assert load_commands(tmp_path)


def test_wrong_validation_stage_and_missing_session_value_fail(tmp_path: Path) -> None:
    for replacement in (
        "--stage review written",
        "--session --stage written",
        "--session january --stage written --price-run prices",
    ):
        events = passing_events("approve")
        events[-1] = event(
            f"sh {PLUGIN}/runtime/launch.sh validate --workspace /app/ledger {replacement}"
        )
        save(tmp_path, events)
        assert not grade_trace(tmp_path, "approve")["passed"]


@pytest.mark.parametrize("suffix", ["; true", "\ntrue"])
def test_later_success_cannot_hide_command_failure(tmp_path: Path, suffix: str) -> None:
    events = passing_events("init")
    events[-1] = event(
        f"false && sh {PLUGIN}/runtime/launch.sh init --workspace /app/ledger{suffix}"
    )
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


def test_listing_skills_does_not_count_as_reading(tmp_path: Path) -> None:
    events = passing_events("init")
    events[0] = event(f"rg --files {PLUGIN}/skills/auto-bean-init/SKILL.md")
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


def test_shell_star_cannot_claim_reads_in_subdirectories(tmp_path: Path) -> None:
    events = passing_events("init")
    events[2] = event("cat *")
    save(tmp_path, events)
    report = grade_trace(tmp_path, "init")
    assert not report["passed"]
    assert not next(
        c
        for c in report["checks"]
        if c["requirement"] == "fresh:.auto-bean/workspace.json"
    )["passed"]


@pytest.mark.parametrize("separator", ["'&&'", "';'"])
def test_quoted_shell_separator_is_only_output(tmp_path: Path, separator: str) -> None:
    events = passing_events("init")
    events[-1] = event(
        f"echo {separator} sh {PLUGIN}/runtime/launch.sh init --workspace /app/ledger"
    )
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


def test_all_tasks_transfer_native_trace_and_use_default_gate() -> None:
    import tomllib

    harbor = Path(__file__).resolve().parents[1]
    tasks = sorted((harbor / "tasks").glob("*/task.toml"))
    assert len(tasks) == 4
    for task in tasks:
        config = tomllib.loads(task.read_text())
        assert "/logs/agent" in config["artifacts"]
        for entry in task.parent.rglob("tests/test.sh"):
            assert "verify.py" in entry.read_text()
            assert "state-only" not in entry.read_text()
    dockerfile = (harbor / "environment/Dockerfile").read_text()
    assert "COPY evals/harbor/trace.py /opt/evals/harbor/trace.py" in dockerfile


def test_command_help_is_not_workflow_execution(tmp_path: Path) -> None:
    events = passing_events("init")
    events[-1] = event(
        f"sh {PLUGIN}/runtime/launch.sh init --workspace /app/ledger --help"
    )
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


def test_prior_reads_need_snapshot_evidence_for_reuse(
    tmp_path: Path,
) -> None:
    events = passing_events("approve")
    context = events[2]
    context["timestamp"] = "2026-10-21T09:01:00Z"
    events.append(
        event(
            "cat ledger.beancount statements/import-status.yml .auto-bean/workspace.json beancount/accounts.beancount .auto-bean/memory/MEMORY.md"
        )
    )
    save(tmp_path, events)
    assert grade_trace(tmp_path, "approve")["passed"]
    events.pop()
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "approve")["passed"]


@pytest.mark.parametrize("phase", ["correct", "approve", "stale"])
@pytest.mark.parametrize("changed", [False, True])
def test_boundary_reuses_unchanged_content_but_refreshes_external_changes(
    tmp_path: Path, phase: str, changed: bool
) -> None:
    events = passing_events(phase)
    # A review input was inspected in an earlier turn. A new user message alone
    # does not require another read; an external edit does.
    events[3] = event("cat statements/parsed/january.json", timestamp=START)
    events[3]["timestamp"] = "2026-10-21T09:00:00Z"
    events[3]["payload"]["item"]["aggregated_output"] = '{"review":"original"}\n'
    events.append(
        event(
            "cat .auto-bean/memory/account_mappings.json .auto-bean/memory/category_mappings.json"
        )
    )
    save(tmp_path, events)
    snapshot = '{"review":"changed"}\n' if changed else '{"review":"original"}\n'
    report = grade_trace(
        tmp_path,
        phase,
        contents=lambda path: (
            snapshot if path == "/app/ledger/statements/parsed/january.json" else None
        ),
    )
    assert report["passed"] is not changed, report
    if changed:
        events.append(event("cat statements/parsed/january.json"))
        save(tmp_path, events)
        assert grade_trace(tmp_path, phase, contents=lambda _: snapshot)["passed"]


def native_change(*, tool: bool = False, timestamp: str = NOW) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": "change-test",
        "status": "completed",
        "type": "FileChange",
        "changes": [
            {
                "path": "/app/ledger/statements/parsed/january.json",
                "diff": "-old\n+new\n",
            }
        ],
    }
    if tool:
        item = {
            "id": "tool-test",
            "status": "completed",
            "type": "McpToolCall",
            "server": "import_review",
            "tool": "update_import_review",
            "result": {
                "isError": False,
                "structuredContent": {
                    "status": "ok",
                    "changed_files": ["statements/parsed/january.json"],
                    "file_sha256": {
                        "statements/parsed/january.json": hashlib.sha256(
                            b"new\n"
                        ).hexdigest()
                    },
                },
            },
        }
    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {"type": "item_completed", "item": item},
    }


@pytest.mark.parametrize("tool", [False, True])
@pytest.mark.parametrize(
    "defect", [None, "failed", "narration", "unrelated", "outside"]
)
def test_agent_knows_its_edits_and_reported_tool_changes(
    tmp_path: Path, tool: bool, defect: str | None
) -> None:
    events = passing_events("stale")
    events.pop(3)
    change = native_change(tool=tool)
    if defect == "failed":
        change["payload"]["item"]["status"] = "failed"
    elif defect == "narration":
        change["type"] = "response_item"
    elif defect == "outside":
        if tool:
            change["payload"]["item"]["result"]["structuredContent"][
                "changed_files"
            ] = ["../ledger/statements/parsed/january.json"]
        else:
            change["payload"]["item"]["changes"][0]["path"] = (
                "../ledger/statements/parsed/january.json"
            )
    if defect == "unrelated":
        path = save(tmp_path, [change], child=True)
        path.write_text(
            path.read_text().replace(
                '"parent_thread_id": "root"', '"parent_thread_id": "stranger"'
            )
        )
    else:
        events.append(change)
    save(tmp_path, events)
    report = grade_trace(tmp_path, "stale")
    assert report["passed"] is (defect is None), report


@pytest.mark.parametrize("snapshot", ["new\n", "external\n", None])
def test_reported_change_carries_forward_only_while_digest_matches(
    tmp_path: Path, snapshot: str | None
) -> None:
    events = passing_events("approve")
    events[3] = event(
        "cat .auto-bean/memory/account_mappings.json .auto-bean/memory/category_mappings.json"
    )
    events.append(native_change(tool=True, timestamp="2026-10-21T09:00:00Z"))
    save(tmp_path, events)
    report = grade_trace(tmp_path, "approve", contents=lambda _: snapshot)
    assert report["passed"] is (snapshot == "new\n"), report


def test_tool_receipt_compares_exact_bytes_including_line_endings(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "ledger"
    parsed = ledger / "statements/parsed/january.json"
    parsed.parent.mkdir(parents=True)
    parsed.write_bytes(b"new\r\n")
    events = passing_events("stale")
    events.pop(3)
    change = native_change(tool=True, timestamp="2026-10-21T09:00:00Z")
    manifest = change["payload"]["item"]["result"]["structuredContent"]
    manifest["file_sha256"]["statements/parsed/january.json"] = hashlib.sha256(
        b"new\r\n"
    ).hexdigest()
    events.append(change)
    save(tmp_path, events)
    assert grade_trace(
        tmp_path, "stale", contents=snapshot_reader(ledger, tmp_path / "plugin")
    )["passed"]


def test_hash_or_narrated_change_alone_does_not_establish_inspection(
    tmp_path: Path,
) -> None:
    events = passing_events("stale")
    events[3] = event("sha256sum statements/parsed/january.json")
    events[3]["payload"]["item"]["aggregated_output"] = json.dumps(
        {"changed_files": ["statements/parsed/january.json"]}
    )
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "stale")["passed"]


@pytest.mark.parametrize("snapshot", ["new\n", "external\n"])
def test_prior_agent_edit_preserves_knowledge_across_boundary(
    tmp_path: Path, snapshot: str
) -> None:
    events = passing_events("approve")
    events[3] = event(
        "cat .auto-bean/memory/account_mappings.json .auto-bean/memory/category_mappings.json"
    )
    read = event("cat statements/parsed/january.json", timestamp="2026-10-21T09:00:00Z")
    read["payload"]["item"]["aggregated_output"] = "old\n"
    edit = native_change(timestamp="2026-10-21T09:01:00Z")
    edit["payload"]["item"]["changes"][0]["diff"] = "@@ -1 +1 @@\n-old\n+new\n"
    events.extend([read, edit])
    save(tmp_path, events)
    report = grade_trace(tmp_path, "approve", contents=lambda _: snapshot)
    assert report["passed"] is (snapshot == "new\n"), report


@pytest.mark.parametrize(
    "diff",
    [
        "-old\n+new\n",
        "@@ -1,2 +1 @@\n-old\n+new\n",
        "@@ -1 +1 @@\n-other\n+new\n",
        "@@ -8 +8 @@\n-old\n+new\n",
    ],
)
def test_incomplete_or_conflicting_patch_cannot_prove_freshness(diff: str) -> None:
    assert patch_content("old\n", diff) is None


@pytest.mark.parametrize(
    ("original", "diff", "expected"),
    [
        ("", "@@ -0,0 +1 @@\n+new\n", "new\n"),
        ("a\nc\n", "@@ -1,0 +2 @@\n+b\n", "a\nb\nc\n"),
        ("a\nb\nc\n", "@@ -2 +1,0 @@\n-b\n", "a\nc\n"),
        ("a\nb\nc\n", "@@ -1 +1 @@\n-a\n+A\n@@ -3 +3 @@\n-c\n+C\n", "A\nb\nC\n"),
    ],
)
def test_unified_patch_reconstruction(original: str, diff: str, expected: str) -> None:
    assert patch_content(original, diff) == expected


@pytest.mark.parametrize("spoof", [False, True])
def test_validator_change_manifest_is_observed_without_reread(
    tmp_path: Path, spoof: bool
) -> None:
    events = passing_events("approve")
    events[3] = event(
        "cat .auto-bean/memory/account_mappings.json .auto-bean/memory/category_mappings.json"
    )
    result = {"state": "passed", "changed_files": ["statements/parsed/january.json"]}
    change = event(
        "echo ignored"
        if spoof
        else f"sh {PLUGIN}/runtime/launch.sh validate --workspace /app/ledger --session january --stage written"
    )
    change["payload"]["item"]["aggregated_output"] = json.dumps(result)
    events.append(change)
    save(tmp_path, events)
    assert grade_trace(tmp_path, "approve")["passed"] is not spoof


@pytest.mark.parametrize(
    "defect", [None, "root_only", "shared_worker", "missing_source", "unrelated_child"]
)
def test_group_stage_delegation_needs_distinct_descendants(
    tmp_path: Path, defect: str | None
) -> None:
    save(tmp_path, passing_events("review"))
    groups = {
        "process": [
            {
                "group_id": "january",
                "paths": ["statements/raw/checking.csv", "statements/raw/savings.pdf"],
            }
        ],
        "categorize": [
            {
                "group_id": "january",
                "paths": [
                    "statements/parsed/january.json",
                    "statements/parsed/january.json",
                ],
            }
        ],
    }
    for stage, entries in groups.items():
        paths = entries[0]["paths"]
        if defect == "missing_source":
            paths = paths[:1]
        events = [
            event(f"cat {PLUGIN}/skills/auto-bean-{stage}/SKILL.md"),
            event("cat " + " ".join(paths)),
        ]
        if defect == "root_only":
            with (tmp_path / "sessions/root.jsonl").open("a") as stream:
                stream.write("".join(json.dumps(e) + "\n" for e in events))
            continue
        path = save(tmp_path, events, child=True)
        records = [json.loads(line) for line in path.read_text().splitlines()]
        records[0]["payload"]["id"] = "shared" if defect == "shared_worker" else stage
        if defect == "unrelated_child":
            records[0]["payload"]["source"]["subagent"]["spawn"]["parent_thread_id"] = (
                "unrelated"
            )
        path.unlink()
        (path.parent / f"{stage}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in records)
        )
    report = grade_trace(tmp_path, "review", groups)
    assert report["passed"] is (defect is None), report


def save_group_workers(logs: Path) -> None:
    for stage, paths in {
        "process": "statements/raw/checking.csv statements/raw/savings.pdf",
        "categorize": "statements/parsed/january.json statements/parsed/january.json",
    }.items():
        path = save(
            logs,
            [
                event(f"cat {PLUGIN}/skills/auto-bean-{stage}/SKILL.md"),
                event(f"cat {paths}"),
            ],
            child=True,
        )
        records = [json.loads(line) for line in path.read_text().splitlines()]
        records[0]["payload"]["id"] = stage
        path.unlink()
        (path.parent / f"{stage}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in records)
        )


def test_distinct_groups_cannot_share_a_stage_worker(tmp_path: Path) -> None:
    save(tmp_path, passing_events("review"))
    save_group_workers(tmp_path)
    groups = {
        "process": [
            {"group_id": "checking", "paths": ["statements/raw/checking.csv"]},
            {"group_id": "savings", "paths": ["statements/raw/savings.pdf"]},
        ],
    }
    report = grade_trace(tmp_path, "review", groups)
    assert not report["passed"]
    # A second descendant can own the savings group independently.
    path = tmp_path / "sessions/process.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines()]
    records[0]["payload"]["id"] = "process-savings"
    (path.parent / "process-savings.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in records)
    )
    assert grade_trace(tmp_path, "review", groups)["passed"]


@pytest.mark.parametrize("field", ["spawn", "thread_spawn"])
def test_cli_parent_metadata_admits_only_linked_descendants(
    tmp_path: Path, field: str
) -> None:
    events = passing_events("review")
    skills = events.pop(0)
    save(tmp_path, events)
    path = save(tmp_path, [skills], child=True)
    path.write_text(path.read_text().replace('"spawn":', f'"{field}":'))
    assert grade_trace(tmp_path, "review")["passed"]
    path.write_text(
        path.read_text().replace(
            '"parent_thread_id": "root"', '"parent_thread_id": "other"'
        )
    )
    assert not grade_trace(tmp_path, "review")["passed"]


@pytest.mark.parametrize(
    "wrapper", ["timeout 60", "timeout 120", "/usr/bin/timeout 2m"]
)
def test_timeout_preserves_successful_extraction_evidence(
    tmp_path: Path, wrapper: str
) -> None:
    events = passing_events("review")
    for row in events:
        item = row["payload"]["item"]
        if " docling " in item["command"][2]:
            item["command"][2] = wrapper + " " + item["command"][2]
    save(tmp_path, events)
    assert grade_trace(tmp_path, "review")["passed"]
    events[-3]["payload"]["item"]["exit_code"] = 124
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "review")["passed"]


@pytest.mark.parametrize(
    "wrapper",
    ["timeout 0", "timeout --preserve-status 60", "timeout invalid", "echo timeout 60"],
)
def test_unsupported_timeout_is_not_execution_evidence(
    tmp_path: Path, wrapper: str
) -> None:
    events = passing_events("init")
    events[-1]["payload"]["item"]["command"][2] = (
        wrapper + " " + events[-1]["payload"]["item"]["command"][2]
    )
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


HELPER = """auto_bean() {
  if [ "$1" = validate ]; then
    shift
    sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" validate "$@"
  else
    sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" run --workspace "$AUTO_BEAN_WORKSPACE" "$@"
  fi
}"""


@pytest.mark.parametrize("inline", [False, True])
@pytest.mark.parametrize(
    "defect", [None, "fake", "wrong_root", "not_invoked", "masked_failure"]
)
def test_documented_helper_requires_real_invocation(
    tmp_path: Path, inline: bool, defect: str | None
) -> None:
    helper = HELPER
    if inline:
        helper = (
            'auto_bean() { if [ "$1" = validate ]; then shift; '
            'sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" validate "$@"; else '
            'sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" run --workspace "$AUTO_BEAN_WORKSPACE" "$@"; fi; }'
        )
    if defect == "fake":
        helper = helper.replace('sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh"', "echo")
    root = PLUGIN if defect != "wrong_root" else "/app/ledger/fake"
    prefix = f"AUTO_BEAN_PLUGIN={root}; AUTO_BEAN_WORKSPACE=/app/ledger; "
    events = passing_events("review")
    for row in events:
        command = row["payload"]["item"]["command"]
        if "bean-query" not in command[2] and " --stage review" not in command[2]:
            continue
        invocation = (
            command[2]
            .replace(
                f"sh {PLUGIN}/runtime/launch.sh run --workspace /app/ledger",
                "auto_bean",
            )
            .replace(f"sh {PLUGIN}/runtime/launch.sh", "auto_bean")
        )
        command[2] = prefix + helper + ("; " if inline else "\n") + invocation
        if defect == "not_invoked":
            command[2] = prefix + helper
        elif defect == "masked_failure":
            command[2] += "; true"
    save(tmp_path, events)
    assert grade_trace(tmp_path, "review")["passed"] is (defect is None)


@pytest.mark.parametrize("defect", [None, "body_only", "failed", "wrong_helper"])
def test_helper_survives_python_heredoc_before_validation(
    tmp_path: Path, defect: str | None
) -> None:
    events = passing_events("review")
    prefix = f"AUTO_BEAN_PLUGIN={PLUGIN} AUTO_BEAN_WORKSPACE=/app/ledger; "
    helper = (
        'auto_bean() { if [ "$1" = validate ]; then shift; '
        'sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" validate "$@"; else '
        'sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" run --workspace "$AUTO_BEAN_WORKSPACE" "$@"; fi; }'
    )
    body = "print('prepared proposals')"
    if defect == "body_only":
        body += "\nprint('auto_bean validate --workspace /app/ledger --session january --stage review')"
        suffix = ""
    else:
        suffix = "\n auto_bean validate --workspace /app/ledger --session january --stage review"
    if defect == "wrong_helper":
        helper = helper.replace('sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh"', "echo")
    events[-1] = event(
        prefix + helper + "; auto_bean python - <<'PY'\n" + body + "\nPY" + suffix,
        code=1 if defect == "failed" else 0,
    )
    save(tmp_path, events)
    assert grade_trace(tmp_path, "review")["passed"] is (defect is None)


@pytest.mark.parametrize(
    "defect", [None, "redirect", "missing", "changed", "body_mention"]
)
def test_literal_cat_prefix_before_launcher_query(
    tmp_path: Path, defect: str | None
) -> None:
    events = passing_events("review")
    events[2] = event(
        "cat ledger.beancount .auto-bean/workspace.json statements/import-status.yml .auto-bean/memory/MEMORY.md"
    )
    script = (
        "cat beancount/accounts.beancount && cat beancount/opening-balances.beancount && "
        f"AUTO_BEAN_PLUGIN={PLUGIN}; "
        'sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" run --workspace /app/ledger '
        'bean-query ledger.beancount "SELECT account, sum(position) GROUP BY account"'
    )
    accounts, opening = (
        "1970-01-01 open Assets:Checking EUR\n",
        "Opening balance evidence\n",
    )
    output = accounts + opening + "Query output\n"
    if defect == "redirect":
        script = script.replace(
            "cat beancount/accounts.beancount",
            "cat beancount/accounts.beancount >/dev/null",
        )
    elif defect == "missing":
        output = (
            "cat: beancount/accounts.beancount: No such file or directory\n" + output
        )
    elif defect == "body_mention":
        script = "python - <<'PY'\nprint('cat beancount/accounts.beancount')\nPY"
    row = event(script)
    row["payload"]["item"]["aggregated_output"] = output
    events.append(row)
    save(tmp_path, events)
    contents = {
        "/app/ledger/beancount/accounts.beancount": accounts
        if defect != "changed"
        else "Changed accounts\n",
        "/app/ledger/beancount/opening-balances.beancount": opening,
    }
    # Queries can supply account evidence independently. Test the cat evidence
    # itself so a valid query cannot hide a broken read recognizer.
    assert any(
        workspace_fresh(c, "beancount/accounts.beancount")
        for c in load_commands(tmp_path, contents=contents.get)
    ) is (defect is None)


def test_assignments_survive_semicolons_but_prior_commands_do_not() -> None:
    script = f'AUTO_BEAN_PLUGIN={PLUGIN}; cat ignored; sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" ensure-runtime --workspace /app/ledger --extraction'
    commands = shell_commands(script, "/app/ledger")
    assert len(commands) == 1
    assert commands[0][0][1] == PLUGIN + "/runtime/launch.sh"
    commands = shell_commands(
        f'false && AUTO_BEAN_PLUGIN={PLUGIN}; sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" init --workspace /app/ledger',
        "/app/ledger",
    )
    assert commands[0][0][1].startswith("$AUTO_BEAN_PLUGIN")


def test_command_prefix_environment_does_not_leak_to_later_commands() -> None:
    prefix = f"AUTO_BEAN_PLUGIN={PLUGIN} AUTO_BEAN_WORKSPACE=/app/ledger "
    commands = shell_commands(
        prefix
        + f"sh {PLUGIN}/runtime/launch.sh ensure-runtime --workspace /app/ledger --extraction",
        "/app/ledger",
    )
    assert commands[0][0][1] == PLUGIN + "/runtime/launch.sh"
    commands = shell_commands(
        prefix
        + 'true; sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" init --workspace /app/ledger',
        "/app/ledger",
    )
    assert commands[0][0][1].startswith("$AUTO_BEAN_PLUGIN")


@pytest.mark.parametrize("defect", [None, "failed", "semicolon", "newline"])
def test_launcher_assignment_in_successful_and_chain(
    tmp_path: Path, defect: str | None
) -> None:
    events = passing_events("correct")
    events = [
        row
        for row in events
        if " bean-query " not in row["payload"]["item"]["command"][2]
    ]
    script = (
        "git status --short && git ls-files statements/raw && "
        f"AUTO_BEAN_PLUGIN={PLUGIN} && "
        'sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" run --workspace /app/ledger '
        'bean-query ledger.beancount "SELECT account, sum(position) GROUP BY account"'
    )
    if defect in {"semicolon", "newline"}:
        separator = "; " if defect == "semicolon" else "\n"
        script = script.replace("git status --short", "false").replace(
            f"{PLUGIN} && ", f"{PLUGIN}{separator}"
        )
    events.append(event(script, code=1 if defect == "failed" else 0))
    save(tmp_path, events)
    assert grade_trace(tmp_path, "correct")["passed"] is (defect is None)


@pytest.mark.parametrize("timeout", ["", "timeout 60 ", "timeout 120 "])
@pytest.mark.parametrize(
    "defect", [None, "definition_only", "failed", "masked", "different_body"]
)
def test_native_run_wrapper_variants(
    tmp_path: Path, timeout: str, defect: str | None
) -> None:
    events = passing_events("review")
    for row in events:
        item = row["payload"]["item"]
        script = item["command"][2]
        if " docling " not in script:
            continue
        helper = f'auto_bean() {{ {timeout}sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" run --workspace "$AUTO_BEAN_WORKSPACE" "$@"; }}'
        invocation = "auto_bean " + script.split("/app/ledger ", 1)[1]
        if defect == "different_body":
            helper = helper.replace('"$@"', '"$@"; true')
        if defect == "definition_only":
            invocation = ""
        if defect == "masked":
            invocation += "; true"
        item["command"][2] = (
            f"AUTO_BEAN_PLUGIN={PLUGIN}; AUTO_BEAN_WORKSPACE=/app/ledger; {helper}; {invocation}"
        )
        if defect == "failed":
            item["exit_code"] = 124
            item["status"] = "failed"
    save(tmp_path, events)
    assert grade_trace(tmp_path, "review")["passed"] is (defect is None)


@pytest.mark.parametrize("separator", ["; ", "\n", " && "])
def test_native_cat_sequence_retains_earlier_reads(
    tmp_path: Path, separator: str
) -> None:
    events = passing_events("init")
    events[0] = event(
        separator.join(
            [
                f"cat {PLUGIN}/skills/auto-bean-init/SKILL.md",
                f"cat {PLUGIN}/references/common.md",
            ]
        )
    )
    save(tmp_path, events)
    assert grade_trace(tmp_path, "init")["passed"]


@pytest.mark.parametrize(
    "defect",
    ["missing", "short_circuit", "redirect", "opaque", "truncated", "unfinished"],
)
def test_cat_recovery_does_not_credit_missing_or_hidden_reads(
    tmp_path: Path, defect: str
) -> None:
    target = f"{PLUGIN}/skills/auto-bean-init/SKILL.md"
    script = f"cat {target}; cat ledger.beancount"
    output = "ledger contents\n"
    code = 0
    if defect == "missing":
        output = f"cat: {target}: No such file or directory\n" + output
    elif defect == "short_circuit":
        script = f"cat missing && cat {target}; cat ledger.beancount"
        output = "cat: missing: No such file or directory\n" + output
    elif defect == "redirect":
        script = f"cat {target} >/dev/null; cat ledger.beancount"
    elif defect == "opaque":
        script = f"false && cat {target}; printf 'fake skill content'"
    elif defect == "truncated":
        output = "100 tokens truncated\n" + output
    events = passing_events("init")
    events[0] = event(script, code=code)
    events[0]["payload"]["item"]["aggregated_output"] = output
    if defect == "unfinished":
        events[0]["payload"]["item"]["status"] = "in_progress"
        events[0]["payload"]["item"]["exit_code"] = None
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


def test_failed_search_retains_content_proven_prefix_reads(tmp_path: Path) -> None:
    target = f"{PLUGIN}/skills/auto-bean-init/SKILL.md"
    events = passing_events("init")
    events[0] = event(
        f"cat {target} && git status --short && rg -n absent other.txt", code=1
    )
    item = events[0]["payload"]["item"]
    item["status"] = "failed"
    item["aggregated_output"] = "full skill instructions\n"
    save(tmp_path, events)
    contents = {target: "full skill instructions\n"}
    assert grade_trace(tmp_path, "init", contents=contents.get)["passed"]
    assert not grade_trace(tmp_path, "init")["passed"]
    contents[target] = "changed instructions\n"
    assert not grade_trace(tmp_path, "init", contents=contents.get)["passed"]
    item["command"][2] = f"false && cat {target}; echo 'full skill instructions'"
    save(tmp_path, events)
    contents[target] = "full skill instructions\n"
    assert not grade_trace(tmp_path, "init", contents=contents.get)["passed"]


@pytest.mark.parametrize(
    "script,code",
    [
        (
            "pwd && git status --short && git ls-files statements/raw && "
            "git ls-files --others --exclude-standard statements/raw && "
            "cat .auto-bean/workspace.json && ls .auto-bean/import-sessions && "
            "cat never-reached.json",
            2,
        ),
        (
            "cat .auto-bean/workspace.json; git status --short; "
            "git ls-files statements/raw; ls -la statements/raw; cat schema.json",
            0,
        ),
        (
            "rg --files references | sort; "
            "cat ledger.beancount .auto-bean/workspace.json; cat schema.json",
            0,
        ),
        ("cat .auto-bean/workspace.json\ngit status --short\nls statements/raw", 0),
    ],
)
def test_snapshot_proves_reads_in_mixed_native_sequences(
    tmp_path: Path, script: str, code: int
) -> None:
    events = passing_events("init")
    events[2] = event("cat ledger.beancount")
    recovered = event(script, code=code)
    recovered["payload"]["item"]["aggregated_output"] = (
        '/app/ledger\n?? setup.sh\n{\n  "format_version": 1\n}\n'
        "ls: cannot access '.auto-bean/import-sessions': No such file or directory\n"
        if code
        else '{\n  "format_version": 1\n}\nother output\n'
    )
    events.append(recovered)
    save(tmp_path, events)
    contents = {
        "/app/ledger/.auto-bean/workspace.json": '{\n  "format_version": 1\n}\n'
    }
    report = grade_trace(tmp_path, "init", contents=contents.get)
    assert report["passed"], report
    check = next(
        c
        for c in report["checks"]
        if c["requirement"] == "fresh:.auto-bean/workspace.json"
    )
    assert "native_output_content" in check["detail"]
    assert not grade_trace(tmp_path, "init")["passed"]
    contents["/app/ledger/.auto-bean/workspace.json"] = "changed snapshot\n"
    assert not grade_trace(tmp_path, "init", contents=contents.get)["passed"]


@pytest.mark.parametrize(
    "script",
    [
        "cat missing && cat .auto-bean/workspace.json; git status --short",
        "cat missing &&\ncat .auto-bean/workspace.json; git status --short",
        "cat missing && rg --files . | sort && cat .auto-bean/workspace.json; git status --short",
        "cat .auto-bean/workspace.json | sort; git status --short",
        "false && cat .auto-bean/workspace.json; echo marker",
        "cat .auto-bean/workspace.json >/dev/null; ls",
        "cat .auto-bean/workspace.json; rg --files --pre malicious .",
        "cat .auto-bean/workspace.json; sort -o overwritten.txt",
        "cat .auto-bean/workspace.json; git -c core.fsmonitor=malicious status",
        "cd /other; cat .auto-bean/workspace.json; ls",
        "echo 'cat .auto-bean/workspace.json'; ls",
    ],
)
def test_snapshot_output_cannot_prove_skipped_or_opaque_reads(
    tmp_path: Path, script: str
) -> None:
    events = passing_events("init")
    events[2] = event("cat ledger.beancount")
    fake = event(script)
    fake["payload"]["item"]["aggregated_output"] = (
        'cat: missing: No such file or directory\n{\n  "format_version": 1\n}\n'
    )
    events.append(fake)
    save(tmp_path, events)
    contents = {
        "/app/ledger/.auto-bean/workspace.json": '{\n  "format_version": 1\n}\n'
    }
    assert not grade_trace(tmp_path, "init", contents=contents.get)["passed"]


@pytest.mark.parametrize(
    "defect", ["truncated", "partial", "failed_operand", "unfinished"]
)
def test_mixed_read_requires_complete_terminal_output(
    tmp_path: Path, defect: str
) -> None:
    events = passing_events("init")
    events[2] = event("cat ledger.beancount")
    row = event("cat .auto-bean/workspace.json; git status --short")
    item = row["payload"]["item"]
    content = '{\n  "format_version": 1\n}\n'
    item["aggregated_output"] = content
    if defect == "truncated":
        item["aggregated_output"] += "100 tokens truncated\n"
    elif defect == "partial":
        item["aggregated_output"] = content[:10]
    elif defect == "failed_operand":
        item["aggregated_output"] += (
            "cat: .auto-bean/workspace.json: Permission denied\n"
        )
    else:
        item.update(status="in_progress", exit_code=None)
    events.append(row)
    save(tmp_path, events)
    contents = {"/app/ledger/.auto-bean/workspace.json": content}
    assert not grade_trace(tmp_path, "init", contents=contents.get)["passed"]


@pytest.mark.parametrize(
    "command",
    [
        "git -C /app/ledger status --short --branch",
        "git --no-pager -C /app/ledger status --short",
        "git -C . status --porcelain",
        "git -C /app -C ledger status --short",
    ],
)
def test_git_status_resolves_literal_working_directory(
    tmp_path: Path, command: str
) -> None:
    events = passing_events("init")
    events[4] = event(command)
    save(tmp_path, events)
    assert grade_trace(tmp_path, "init")["passed"]
    events[4]["payload"]["item"]["exit_code"] = 1
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


@pytest.mark.parametrize(
    "command",
    [
        "git -C /other status --short",
        "git -C /app/ledger status --help",
        "git --git-dir /other/.git status --short",
        "git -c alias.status=malicious status",
        "echo git -C /app/ledger status",
    ],
)
def test_git_options_cannot_redirect_or_replace_workspace_status(
    tmp_path: Path, command: str
) -> None:
    events = passing_events("init")
    events[4] = event(command)
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]


def skill_message(source: str) -> dict[str, Any]:
    return {
        "timestamp": NOW,
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "<skill>\n<name>auto-bean:auto-bean-import</name>\n"
                        f"<path>{PLUGIN}/skills/auto-bean-import/SKILL.md</path>\n"
                        f"{source}\n</skill>"
                    ),
                }
            ],
        },
    }


@pytest.mark.parametrize("child", [False, True])
def test_exact_native_skill_injection_counts_as_loaded_skill(
    tmp_path: Path, child: bool
) -> None:
    source = "---\nname: auto-bean-import\n---\nComplete import instructions.\n"
    events = passing_events("needs-input")
    events[0] = event(
        f"cat {PLUGIN}/skills/{{auto-bean-process,auto-bean-query,auto-bean-categorize}}/SKILL.md"
    )
    injection = skill_message(source)
    save(tmp_path, events if child else [injection, *events])
    if child:
        save(tmp_path, [injection], child=True)
    contents = {f"{PLUGIN}/skills/auto-bean-import/SKILL.md": source}
    report = grade_trace(tmp_path, "needs-input", contents=contents.get)
    assert report["passed"], report
    check = next(c for c in report["checks"] if c["requirement"] == "skill:import")
    assert check["detail"] == "native_skill_injection"
    assert not grade_trace(tmp_path, "needs-input")["passed"]


@pytest.mark.parametrize(
    "defect",
    [
        "changed",
        "truncated",
        "wrong_path",
        "wrong_name",
        "assistant",
        "tool_output",
        "prose",
        "extra_block",
        "unrelated",
    ],
)
def test_skill_injection_requires_exact_source_and_native_session(
    tmp_path: Path, defect: str
) -> None:
    source = "---\nname: auto-bean-import\n---\nComplete import instructions.\n"
    events = passing_events("needs-input")
    events[0] = event(
        f"cat {PLUGIN}/skills/{{auto-bean-process,auto-bean-query,auto-bean-categorize}}/SKILL.md"
    )
    injection = skill_message(source)
    block = injection["payload"]["content"][0]
    if defect == "changed":
        block["text"] = block["text"].replace("Complete", "Forged")
    elif defect == "truncated":
        block["text"] = block["text"].replace(source, source[:15])
    elif defect == "wrong_path":
        block["text"] = block["text"].replace(PLUGIN, "/app/ledger/fake")
    elif defect == "wrong_name":
        block["text"] = block["text"].replace(
            "<name>auto-bean:auto-bean-import", "<name>auto-bean:auto-bean-write"
        )
    elif defect == "assistant":
        injection["payload"]["role"] = "assistant"
    elif defect == "tool_output":
        injection["payload"]["type"] = "function_call_output"
    elif defect == "prose":
        block["text"] = "I loaded this skill:\n" + block["text"]
    elif defect == "extra_block":
        injection["payload"]["content"].append({"type": "input_text", "text": "other"})
    save(tmp_path, [injection, *events] if defect != "unrelated" else events)
    if defect == "unrelated":
        path = save(tmp_path, [injection], child=True)
        path.write_text(
            path.read_text().replace(
                '"parent_thread_id": "root"', '"parent_thread_id": "other"'
            )
        )
    contents = {f"{PLUGIN}/skills/auto-bean-import/SKILL.md": source}
    assert not grade_trace(tmp_path, "needs-input", contents=contents.get)["passed"]


def test_failed_cat_operand_does_not_discard_other_semicolon_reads(
    tmp_path: Path,
) -> None:
    events = passing_events("init")
    events[0] = event(
        f"cat missing; cat {PLUGIN}/skills/auto-bean-init/SKILL.md; cat ledger.beancount"
    )
    events[0]["payload"]["item"]["aggregated_output"] = (
        "cat: missing: No such file or directory\nskill\nledger\n"
    )
    save(tmp_path, events)
    assert grade_trace(tmp_path, "init")["passed"]


def test_snapshot_paths_cannot_escape_roots(tmp_path: Path) -> None:
    from evals.harbor.trace import snapshot_reader

    ledger = tmp_path / "ledger"
    plugin = tmp_path / "plugin"
    ledger.mkdir()
    plugin.mkdir()
    secret = tmp_path / "secret"
    secret.write_text("outside")
    (ledger / "link").symlink_to(secret)
    read = snapshot_reader(ledger, plugin)
    assert read("/app/ledger/link") is None
    assert read("/app/ledger/../secret") is None
    assert read("/etc/passwd") is None
    assert read(PLUGIN + "/references/../../secret") is None


def test_worker_identity_survives_missing_activity_evidence(tmp_path: Path) -> None:
    save(tmp_path, passing_events("review"))
    child = save(tmp_path, [event("echo worker started")], child=True)
    groups = {
        "process": [{"group_id": "january", "paths": ["statements/raw/checking.csv"]}]
    }
    report = grade_trace(tmp_path, "review", groups)
    assert not report["passed"]
    assert [worker["id"] for worker in report["workers"]] == ["child"]
    check = next(
        c
        for c in report["checks"]
        if c["requirement"] == "subagents:separate-group-stage-workers"
    )
    assert "undetermined" in check["detail"]
    child.write_text(
        child.read_text().replace(
            '"parent_thread_id": "root"', '"parent_thread_id": "unrelated"'
        )
    )
    assert grade_trace(tmp_path, "review", groups)["workers"] == []


def test_import_entrypoint_fits_observed_pinned_cli_injection_budget() -> None:
    # CLI 0.163.0 injected only 8,000 characters in the saved 2026-10-21 run.
    # Keep the complete orchestration entrypoint available without truncation.
    skill = (
        Path(__file__).resolve().parents[3]
        / "plugins/auto-bean/skills/auto-bean-import/SKILL.md"
    )
    assert len(skill.read_text()) <= 8000


@pytest.mark.parametrize("prefix", ["", "timeout 60 "])
def test_unresolved_helper_is_not_a_trusted_launcher(
    tmp_path: Path, prefix: str
) -> None:
    events = passing_events("init")
    events[-1] = event(prefix + "auto_bean init --workspace /app/ledger")
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "init")["passed"]
