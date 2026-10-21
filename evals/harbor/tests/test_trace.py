"""Trace checks must distinguish observed actions from claims and prior turns."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.harbor.trace import grade_trace, load_commands

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
        "cat statements/parsed/checking.json statements/parsed/savings.json .auto-bean/memory/account_mappings.json .auto-bean/memory/category_mappings.json",
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
    for replacement in ("--stage review written", "--session --stage written"):
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
        if c["requirement"] == "read:.auto-bean/workspace.json"
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


def test_session_context_can_be_reused_but_ledger_must_be_reread(
    tmp_path: Path,
) -> None:
    events = passing_events("approve")
    context = events[2]
    context["timestamp"] = "2026-10-21T09:01:00Z"
    events.append(event("cat ledger.beancount statements/import-status.yml"))
    save(tmp_path, events)
    assert grade_trace(tmp_path, "approve")["passed"]
    events.pop()
    save(tmp_path, events)
    assert not grade_trace(tmp_path, "approve")["passed"]
