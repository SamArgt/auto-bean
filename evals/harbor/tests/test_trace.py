"""Trace checks must distinguish observed actions from claims and prior turns."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.harbor.trace import grade_trace, load_commands, shell_commands

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
