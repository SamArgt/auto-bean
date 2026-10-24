from __future__ import annotations

import asyncio
import json
import subprocess
import runpy
import os
import shlex
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from unittest.mock import AsyncMock, call

import pytest
import yaml

from auto_bean import init
from auto_bean.common import WorkflowError
from evals.harbor.adapter import AutoBeanCodex
from evals.harbor.fixtures import (
    import_ledger,
    raw_inputs,
    write_json as write_fixture_json,
)
from auto_bean.validation import session_members

from evals.harbor.capture import metadata, checkpoint
from evals.harbor.verify import (
    import_checks,
    account_decisions,
    transaction_decisions,
    init_checks,
    material_hash,
    scenario_checks,
    correction_checks,
    load_ledger,
    STALE_RATIONALE,
    financial_checks,
)

PLUGIN = Path(__file__).resolve().parents[3] / "plugins/auto-bean"
reference = runpy.run_path(
    str(
        PLUGIN.parents[1]
        / "evals/harbor/tasks/import-two-statements/solution/reference.py"
    )
)
approve, draft = reference["approve"], reference["draft"]


def read_fixture(
    path: Path, source: str = "statements/raw/checking.csv"
) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if "group_id" in data and "statements" in data:
        return next(d for d in data["statements"] if d["source_file"] == source)
    return dict(data)


def write_json(path: Path, data: Any) -> None:
    if (
        isinstance(data, dict)
        and "source_file" in data
        and path.parent.name == "parsed"
    ):
        group = json.loads(path.read_text())
        group["statements"] = [
            d if d["source_file"] != data["source_file"] else data
            for d in group["statements"]
        ]
        data = group
    write_fixture_json(path, data)


@pytest.fixture
def reviewed(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    raw_inputs(tmp_path / "raw")
    root = tmp_path / "ledger"
    expected = import_ledger(root, PLUGIN, tmp_path / "raw")
    draft(root, PLUGIN, extract=False)
    evidence = tmp_path / "evidence"
    write_json(evidence / "runtime.json", {"validated": True, "runtime_present": True})
    write_json(evidence / "review.json", checkpoint(root))
    (evidence / "last-response.txt").write_text(
        "checking.csv and savings.pdf reconciled; bean-check passed.\n\n---\n\n"
        "## Import Status: Ready For Review\n\n**Summary:** Both statements reviewed.\n**Next Step:** Approve the reviewed transactions.\n"
    )
    return root, evidence, expected


def complete(root: Path, evidence: Path) -> None:
    approve(root, evidence / "review.json")
    (evidence / "last-response.txt").write_text(
        "---\n\n## Import Status: Complete\n\n**Summary:** Both statements done.\n**Next Step:** None.\n"
    )


def test_review_and_approval_semantic_verifiers(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    import_checks(root, PLUGIN, evidence, expected, "review")
    complete(root, evidence)
    import_checks(root, PLUGIN, evidence, expected, "approve")


def test_review_identifies_statements_without_requiring_literal_filenames(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    response = evidence / "last-response.txt"
    text = response.read_text().replace(
        "checking.csv and savings.pdf", "Checking CSV and Savings PDF"
    )
    response.write_text(text)
    import_checks(root, PLUGIN, evidence, expected, "review")
    response.write_text(text.replace(" and Savings PDF", ""))
    with pytest.raises(AssertionError, match="omits one statement"):
        import_checks(root, PLUGIN, evidence, expected, "review")


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "scope",
        "source",
        "approval",
        "provisional",
        "early",
        "duplicate",
        "conflicting",
    ],
)
def test_memory_uses_actual_governed_records(
    reviewed: tuple[Path, Path, dict[str, Any]], defect: str
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    path = root / ".auto-bean/memory/category_mappings.json"
    data = read_fixture(path)
    record = data["records"][0]
    if defect == "missing":
        data["records"] = []
    elif defect == "scope":
        record["scope"] = {"currency": "EUR"}
    elif defect == "source":
        record["source"]["source_fingerprint"] = "sha256:" + "0" * 64
    elif defect == "approval":
        record["audit"]["review_digest"] = "0" * 64
    elif defect == "provisional":
        record["review_state"] = "observed"
    elif defect == "early":
        record["created_at"] = "2020-01-01T00:00:00Z"
    elif defect == "duplicate":
        data["records"].append({**record, "record_id": "duplicate-learning"})
    else:
        data["records"].append(
            {
                **record,
                "record_id": "conflicting-learning",
                "decision": {
                    **record["decision"],
                    "posting_account": "Expenses:Bank-Fees",
                },
            }
        )
    write_json(path, data)
    with pytest.raises(AssertionError, match="memory"):
        import_checks(root, PLUGIN, evidence, expected, "approve")


def test_unapplied_decisions_cannot_be_learned(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    learned = json.loads((root / ".auto-bean/memory/account_mappings.json").read_text())
    # Restore the review checkpoint and baseline, retaining only premature memory.
    checkpoint_data = json.loads((evidence / "review.json").read_text())
    for name, content in checkpoint_data["baseline_contents"].items():
        (root / name).write_text(content)
    (root / "beancount/imports.beancount").unlink()
    (root / "statements/import-status.yml").write_text(checkpoint_data["status"])
    for member in session_members(checkpoint_data["session"]):
        write_json(
            root / member["parsed_group"],
            checkpoint_data["documents"][member["source_file"]],
        )
    write_json(
        root / ".auto-bean/import-sessions/harbor-import.json",
        checkpoint_data["session"],
    )
    write_json(root / ".auto-bean/memory/account_mappings.json", learned)
    with pytest.raises(AssertionError, match="Unapplied decisions"):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_memory_learning_retains_ids_and_audit_on_replay(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, _ = reviewed
    complete(root, evidence)
    paths = [
        root / ".auto-bean/memory" / name
        for name in ("account_mappings.json", "category_mappings.json")
    ]
    before = {path: path.read_bytes() for path in paths}
    approve(root, evidence / "review.json")
    assert all(path.read_bytes() == content for path, content in before.items())


def test_epilogues_are_required_at_completion_not_before_user_approval(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    import_checks(root, PLUGIN, evidence, expected, "review")
    complete(root, evidence)
    path = root / ".auto-bean/import-sessions/harbor-import.json"
    doc = read_fixture(path)
    doc["price_runs"] = []
    write_json(path, doc)
    with pytest.raises(AssertionError, match="prices stage"):
        import_checks(root, PLUGIN, evidence, expected, "approve")


def test_noop_cannot_pass(
    reviewed: tuple[Path, Path, dict[str, Any]], tmp_path: Path
) -> None:
    _, evidence, _ = reviewed
    raw_inputs(tmp_path / "fresh-raw")
    root = tmp_path / "fresh-ledger"
    expected = import_ledger(root, PLUGIN, tmp_path / "fresh-raw")
    with pytest.raises(AssertionError, match="exactly the two"):
        import_checks(root, PLUGIN, evidence, expected, "review")
    with pytest.raises(AssertionError):
        init_checks(tmp_path / "absent", PLUGIN, evidence)


def test_premature_done_fails(reviewed: tuple[Path, Path, dict[str, Any]]) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    with pytest.raises(AssertionError, match="final_review"):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_raw_changes_fail(reviewed: tuple[Path, Path, dict[str, Any]]) -> None:
    root, evidence, expected = reviewed
    (root / "statements/raw/checking.csv").write_text("tampered source")
    with pytest.raises(AssertionError, match="Preserved file changed"):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_invalid_parsed_state_fails(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    path = root / "statements/parsed/january.json"
    data = read_fixture(path)
    data["extracted_records"][0]["account_id"] = "missing-account"
    write_json(path, data)
    with pytest.raises(Exception, match="account_id"):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_init_grades_actual_scaffold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "new ledger"
    monkeypatch.setattr(init, "ensure_runtime", lambda root: tmp_path / "runtime")
    monkeypatch.setattr(init, "validate", lambda root, runtime: None)
    init.initialize(root)
    evidence = tmp_path / "evidence"
    write_json(evidence / "runtime.json", {"validated": True, "runtime_present": True})
    init_checks(root, PLUGIN, evidence)
    accounts = root / "beancount/accounts.beancount"
    original = accounts.read_text()
    accounts.write_text(original.replace("Assets:Checking", "Assets:Other"))
    with pytest.raises(AssertionError, match="default accounts"):
        init_checks(root, PLUGIN, evidence)
    accounts.write_text(original)
    (root / "beancount/opening-balances.beancount").write_text(
        '2026-01-01 * "Invented"\n  Assets:Checking 1 EUR\n  Equity:Opening-Balances -1 EUR\n'
    )
    with pytest.raises(AssertionError, match="invented"):
        init_checks(root, PLUGIN, evidence)


def test_tasks_run_directly_and_keep_grading_out_of_agent_images() -> None:
    from harbor.models.task.task import Task
    from harbor.agents.oracle import OracleAgent

    root = PLUGIN.parents[1]
    suite = root / "evals/harbor"
    tasks = [
        Task(suite / "tasks" / name)
        for name in (
            "init-ledger",
            "import-two-statements",
            "human-input-correction",
            "stale-review",
        )
    ]
    assert not tasks[0].has_steps
    assert tasks[1].has_steps
    assert tasks[1].config.multi_step_reward_strategy == "mean"
    assert tasks[1].config.steps and tasks[1].config.steps[0].min_reward == {
        "state": 1.0
    }
    for task, names in zip(
        tasks[1:],
        (
            ("review", "approve"),
            ("needs-input", "correct", "approve"),
            ("review", "stale"),
        ),
    ):
        assert task.config.steps
        assert tuple(step.name for step in task.config.steps) == names
        assert task.config.multi_step_reward_strategy == "mean"
        assert all(step.min_reward == {"state": 1.0} for step in task.config.steps[:-1])
        for name in names:
            marker = (
                suite
                / "tasks"
                / task.config.task.name.split("/")[-1]
                / "steps"
                / name
                / "workdir/setup.sh"
            )
            assert f'printf "{name}\\n"' in marker.read_text()
    # Oracle falls back to one shared solution directory for both steps.
    oracle = object.__new__(OracleAgent)
    oracle._task = tasks[1]
    for index in (0, 1):
        oracle._step_index = index
        solution, script = oracle._resolve_solution_paths()
        assert script == solution / "solve.sh"
        assert (solution / "reference.py").is_file()
        tasks[1].paths.validate_input_tree(solution)
    for compose in (suite / "tasks").rglob("docker-compose.yaml"):
        service = yaml.safe_load(compose.read_text())["services"]["main"]
        build = service["build"]
        context = build["context"].replace("${CONTEXT_DIR}", str(compose.parent))
        assert Path(context).resolve() == root
        assert build["dockerfile"] == "evals/harbor/environment/Dockerfile"
        assert service["pull_policy"] == "never"
        if compose.parent.name == "tests":
            assert service["image"] == "auto-bean-harbor-verifier:local"
            assert "args" not in build
            assert service["environment"]["AUTO_BEAN_EVAL_PHASE"] == (
                "init"
                if compose.parent.parent.name == "init-ledger"
                else compose.parent.parent.name
            )
    dockerfile = (suite / "environment/Dockerfile").read_text()
    agent_stages, verifier_stage = dockerfile.split("FROM ledger-base AS verifier")
    assert "COPY plugins/auto-bean /opt/" in agent_stages
    assert "COPY evals/harbor/verify.py" not in agent_stages
    assert "reference.py" not in dockerfile
    assert "COPY evals/harbor/verify.py" in verifier_stage
    assert "HARBOR_TEST_SCRIPT" not in dockerfile
    assert "environment/verify.sh /tests/test.sh" in verifier_stage
    assert "--extraction" not in verifier_stage
    assert "prefetch.py" not in verifier_stage
    assert "npm ci --ignore-scripts" in agent_stages
    assert "cmp /tmp/expected-bundle.html" in agent_stages
    references = list((suite / "tasks").glob("*/solution/*reference.py"))
    assert len(references) == 3 and len({p.read_bytes() for p in references}) == 1
    assert not (suite / "run.py").exists()


def test_native_harbor_config_defaults() -> None:
    from harbor.agents.factory import AgentFactory
    from harbor.models.job.config import JobConfig
    from harbor.models.trial.config import TaskConfig, TrialConfig
    from harbor.viewer.trial_utils import agent_name_from_config

    config = JobConfig.model_validate(
        yaml.safe_load((PLUGIN.parents[1] / "evals/harbor/codex.yaml").read_text())
    )
    assert config.n_attempts == 1
    assert config.n_concurrent_trials == 4
    assert config.agents[0].model_name == "gpt-6.1-sol"
    # The overview links use the reported name, while the Rollouts filter uses
    # the configured name/import path. Keep both equal for this custom agent.
    assert config.agents[0].name == AutoBeanCodex.name() == "auto-bean-codex"
    assert AgentFactory.get_agent_class_from_config(config.agents[0]) is AutoBeanCodex
    trial = TrialConfig(
        task=TaskConfig(path=Path("evals/harbor/tasks/init-ledger")),
        agent=config.agents[0],
    )
    assert agent_name_from_config(trial) == AutoBeanCodex.name()
    assert config.agents[0].resume_trajectory
    assert config.agents[0].kwargs["version"] == "0.163.0"
    # A boolean AUTH flag in agent.env triggers Harbor's secret scrubber,
    # replacing every digit 1 in artifacts. Use its ambient host flag instead.
    assert config.agents[0].env == {}
    assert config.datasets[0].path == Path("evals/harbor/tasks")


def test_stale_setup_uses_managed_python_and_changes_only_review_rationale(
    reviewed: tuple[Path, Path, dict[str, Any]], tmp_path: Path
) -> None:
    root, evidence, _ = reviewed
    suite = PLUGIN.parents[1] / "evals/harbor"
    original = suite / "tasks/stale-review/steps/stale/workdir/setup.sh"
    before = {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "sh").symlink_to("/bin/sh")
    launcher = tools / "launch.sh"
    arguments = tmp_path / "arguments.txt"
    launcher.write_text(
        f"printf '%s\\n' \"$@\" > {shlex.quote(str(arguments))}\n"
        f"exec {shlex.quote(sys.executable)} -\n"
    )
    script = tmp_path / "setup.sh"
    script.write_text(
        original.read_text()
        .replace(
            "/opt/auto-bean-marketplace/plugins/auto-bean/runtime/launch.sh",
            str(launcher),
        )
        .replace("/app/ledger", str(root))
        .replace("/opt/eval-evidence", str(evidence))
    )
    # Neither python nor python3 exists on this PATH, as in the agent image.
    result = subprocess.run(
        ["/bin/bash", str(script)],
        env={**os.environ, "PATH": str(tools)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert arguments.read_text().splitlines() == [
        "run",
        "--workspace",
        str(root),
        "python",
        "-",
    ]
    assert (evidence / "step-name").read_text() == "stale\n"
    changed = []
    for relative, old_bytes in before.items():
        after = (root / relative).read_bytes()
        if after == old_bytes:
            continue
        changed.append(relative)
        expected = json.loads(old_bytes)
        source = next(
            d
            for d in expected["statements"]
            if d["source_file"] == "statements/raw/checking.csv"
        )
        row = next(r for r in source["extracted_records"] if r["record_id"] == "C-001")
        row["review"]["rationale"] = STALE_RATIONALE
        assert json.loads(after) == expected
    assert len(changed) == 1 and changed[0].startswith("statements/parsed/")


@pytest.mark.parametrize("phase", [None, "review", "stale"])
def test_shared_verifier_entrypoint_requires_explicit_phase(
    tmp_path: Path, phase: str | None
) -> None:
    suite = PLUGIN.parents[1] / "evals/harbor"
    arguments = tmp_path / "arguments.txt"
    interpreter = tmp_path / "python"
    interpreter.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {shlex.quote(str(arguments))}\n"
    )
    interpreter.chmod(0o755)
    script = tmp_path / "verify.sh"
    script.write_text(
        (suite / "environment/verify.sh")
        .read_text()
        .replace("/opt/verifier/bin/python", str(interpreter))
    )
    env = {
        key: value for key, value in os.environ.items() if key != "AUTO_BEAN_EVAL_PHASE"
    }
    if phase is not None:
        env["AUTO_BEAN_EVAL_PHASE"] = phase
    result = subprocess.run(
        ["/bin/bash", str(script)], env=env, capture_output=True, text=True
    )
    if phase is None:
        assert result.returncode != 0
        assert not arguments.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert arguments.read_text().splitlines() == [
            "/opt/evals/harbor/verify.py",
            phase,
            "--ledger",
            "/app/ledger",
            "--plugin",
            "/opt/auto-bean-marketplace/plugins/auto-bean",
            "--expected",
            "/opt/expected.json",
        ]


def test_fixture_regeneration_overwrites_previous_files(tmp_path: Path) -> None:
    raw, root = tmp_path / "raw", tmp_path / "ledger"
    raw_inputs(raw)
    expected = import_ledger(root, PLUGIN, raw)
    (raw / "checking.csv").write_text("obsolete")
    (raw / "savings.pdf").write_bytes(b"obsolete")
    (root / "obsolete-result.txt").write_text("old trial")
    (root / "ledger.beancount").write_text("invalid previous fixture")
    raw_inputs(raw)
    assert import_ledger(root, PLUGIN, raw) == expected
    assert not (root / "obsolete-result.txt").exists()


def test_state_gates_continue_without_hiding_earlier_trace_failure() -> None:
    from types import SimpleNamespace
    from harbor.trial.multi_step import MultiStepTrial
    from harbor.trial.trial import Trial
    from harbor.models.trial.result import StepResult
    from harbor.models.verifier.result import VerifierResult

    rewards = [
        {"reward": 0, "state": 1, "trace": 0},
        {"reward": 1, "state": 1, "trace": 1},
    ]
    for scores in rewards:
        assert MultiStepTrial._min_reward_failure(scores, {"state": 1.0}) is None
    assert MultiStepTrial._min_reward_failure({"reward": 1}, {"state": 1.0}) is not None
    trial = SimpleNamespace(
        result=SimpleNamespace(
            step_results=[
                StepResult(
                    step_name=str(index), verifier_result=VerifierResult(rewards=scores)
                )
                for index, scores in enumerate(rewards)
            ]
        )
    )
    combined = Trial._aggregate_step_rewards(trial)
    assert combined is not None
    assert combined.rewards == {"reward": 0.5, "state": 1, "trace": 0.5}


def test_build_metadata_records_current_plugin_without_host_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin, evidence = tmp_path / "plugin", tmp_path / "evidence"
    (plugin / "runtime").mkdir(parents=True)
    (plugin / "runtime/uv.lock").write_text(
        '[[package]]\nname = "example"\nversion = "1.0"\n'
    )
    (plugin / "plugin.json").write_text("old checkout")
    monkeypatch.setattr(
        subprocess, "check_output", lambda *a, **kw: "codex-cli 0.163.0\n"
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    metadata(plugin, evidence)
    before = json.loads((evidence / "build.json").read_text())
    (plugin / "plugin.json").write_text("new uncommitted checkout")
    metadata(plugin, evidence)
    after = json.loads((evidence / "build.json").read_text())
    assert before["plugin_tree_sha256"] != after["plugin_tree_sha256"]
    assert after["runtime_dependencies"] == [{"name": "example", "version": "1.0"}]
    assert after["codex_version"] == "codex-cli 0.163.0"


def test_raw_pdf_and_baseline_are_reproducible(tmp_path: Path) -> None:
    snapshots = []
    for name in ("one", "two"):
        raw_inputs(tmp_path / name / "raw")
        snapshots.append(
            import_ledger(tmp_path / name / "ledger", PLUGIN, tmp_path / name / "raw")
        )
    assert snapshots[0] == snapshots[1]


def test_adapter_reinstalls_after_config_on_every_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from harbor.agents.installed.codex import Codex

    adapter = object.__new__(AutoBeanCodex)
    setup = AsyncMock()
    upload = AsyncMock()
    monkeypatch.setattr(Codex, "_upload_effective_config", upload)
    monkeypatch.setattr(adapter, "exec_as_agent", setup)
    for _ in range(2):
        asyncio.run(
            adapter._upload_effective_config(
                object(), {}, "/tmp/codex-home/config.toml"
            )
        )
    assert upload.await_count == setup.await_count == 2
    assert "plugin add auto-bean@auto-bean" in setup.call_args.kwargs["command"]
    assert setup.call_args.kwargs["env"] == {"CODEX_HOME": "/tmp/codex-home"}


@pytest.mark.parametrize("phase", ["review", "correct", "approve", "stale"])
def test_adapter_captures_native_step_and_protects_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    from harbor.agents.installed.codex import Codex
    from types import SimpleNamespace

    adapter = object.__new__(AutoBeanCodex)
    adapter._resume = True
    adapter.environment_logs_dir = PurePosixPath("/logs/agent")
    adapter.logs_dir = tmp_path / "agent"
    adapter._review_checkpoint = tmp_path / "earlier-review.json"
    run = AsyncMock()
    capture = AsyncMock()
    environment = SimpleNamespace(
        exec=AsyncMock(return_value=SimpleNamespace(stdout=phase)),
        download_file=AsyncMock(),
        upload_file=AsyncMock(),
    )
    monkeypatch.setattr(Codex, "run", run)
    monkeypatch.setattr(adapter, "exec_as_agent", capture)
    asyncio.run(adapter.run("instruction", environment, object()))
    run.assert_awaited_once()
    assert f"--phase {phase}" in capture.call_args.kwargs["command"]
    if phase in {"review", "correct"}:
        assert environment.download_file.await_args_list == [
            call(
                "/opt/eval-evidence/review.html",
                tmp_path / "review-exports" / f"{phase}.html",
            ),
            call(
                "/opt/eval-evidence/review.json",
                tmp_path / "review-checkpoints" / f"{phase}.json",
            ),
        ]
    else:
        environment.upload_file.assert_awaited_once_with(
            tmp_path / "earlier-review.json", "/opt/eval-evidence/review.json"
        )


def test_premature_ledger_writes_fail(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    (root / "ledger.beancount").write_text(
        (root / "ledger.beancount").read_text() + "; premature write\n"
    )
    with pytest.raises(AssertionError, match="before approval"):
        import_checks(root, PLUGIN, evidence, expected, "review")


@pytest.mark.parametrize("defect", ["account", "record", "session", "ownership"])
def test_structured_reference_corruption_fails(
    reviewed: tuple[Path, Path, dict[str, Any]], defect: str
) -> None:
    root, evidence, expected = reviewed
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    if defect == "account":
        account_decisions(doc)["checking"]["ledger_account"] = "Assets:Savings"
    elif defect == "record":
        doc["extracted_records"].append(doc["extracted_records"][0])
    elif defect == "ownership":
        transaction_decisions(doc)["XFER-001"]["posting_owner"] = (
            "statements/raw/savings.pdf"
        )
    else:
        path = root / ".auto-bean/import-sessions/harbor-import.json"
        doc = read_fixture(path)
        doc["groups"][0]["source_files"].pop()
    write_json(path, doc)
    with pytest.raises(Exception):
        import_checks(root, PLUGIN, evidence, expected, "review")


@pytest.mark.parametrize("phase", ["needs-input", "stale"])
def test_noop_scenario_fails(tmp_path: Path, phase: str) -> None:
    raw_inputs(tmp_path / "raw")
    root = tmp_path / "ledger"
    expected = import_ledger(root, PLUGIN, tmp_path / "raw")
    with pytest.raises(AssertionError):
        scenario_checks(root, tmp_path / "evidence", expected, phase)


def test_verifier_rejects_executable_nonstandard_include_before_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from beancount import loader

    (tmp_path / "ledger.beancount").write_text('include "nested/*.txt"\n')
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested/input.txt").write_text('include "payload.data"\n')
    (tmp_path / "nested/payload.data").write_text('plugin "workspace_payload"\n')

    def forbidden_load(*args: object, **kwargs: object) -> None:
        raise AssertionError("Loader must not execute untrusted code")

    monkeypatch.setattr(loader, "load_file", forbidden_load)
    with pytest.raises(AssertionError, match="executable ledger plugin"):
        load_ledger(tmp_path)


def test_transfer_non_owner_resolves_owner_postings(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    delegated_transfer(root, evidence)
    import_checks(root, PLUGIN, evidence, expected, "review")
    complete(root, evidence)
    import_checks(root, PLUGIN, evidence, expected, "approve")


def test_html_review_capture_uses_trusted_exporter(
    reviewed: tuple[Path, Path, dict[str, Any]], tmp_path: Path
) -> None:
    from evals.harbor.capture import write_review_html

    root, _, _ = reviewed
    output = tmp_path / "export/review.html"
    write_review_html(root, output)
    content = output.read_text()
    assert "Import review unavailable" not in content
    assert "checking.csv" in content and "savings.pdf" in content
    assert "Assets:Checking" in content and "Assets:Savings" in content
    assert "final_review" in content


def test_html_capture_isolates_installed_plugin_import(
    reviewed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from evals.harbor.capture import write_review_html

    root, _, _ = reviewed
    observed = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        observed.append(args)
        return subprocess.CompletedProcess(
            args, 0, "<!doctype html><h1>Review</h1>", ""
        )

    monkeypatch.setattr("evals.harbor.capture.subprocess.run", run)
    output = tmp_path / "review.html"
    write_review_html(root, output, PLUGIN)
    assert observed[0][observed[0].index("python") + 1] == "-I"
    assert observed[0][-3] == str(PLUGIN / "runtime")
    assert output.read_text().endswith("<h1>Review</h1>")


def test_html_capture_reports_escaped_export_failure(
    reviewed: tuple[Path, Path, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from evals.harbor.capture import write_review_html

    root, _, _ = reviewed

    def fail(*args: Any) -> str:
        raise ValueError('<script>alert("unavailable")</script>')

    monkeypatch.setattr("auto_bean.review_export.render_review_html", fail)
    output = tmp_path / "review.html"
    write_review_html(root, output)
    content = output.read_text()
    assert "Import review unavailable" in content
    assert "does not indicate a successful import" in content
    assert "<script>" not in content and "&lt;script&gt;" in content


@pytest.mark.parametrize(
    "phase", ["review", "correct", "approve", "needs-input", "stale"]
)
def test_noop_verifier_retains_unavailable_html_for_every_import_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    from evals.harbor.verify import main

    root, logs = tmp_path / "ledger", tmp_path / "logs"
    root.mkdir()
    expected = tmp_path / "expected.json"
    write_json(expected, {})
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify.py",
            phase,
            "--ledger",
            str(root),
            "--plugin",
            str(PLUGIN),
            "--expected",
            str(expected),
            "--logs",
            str(logs),
        ],
    )
    assert main() == 1
    assert (logs / "reward.txt").read_text().strip() == "0"
    assert "Import review unavailable" in (logs / "review.html").read_text()


def test_init_verifier_does_not_export_import_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from evals.harbor.verify import main

    root, logs = tmp_path / "ledger", tmp_path / "logs"
    root.mkdir()
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify.py",
            "init",
            "--ledger",
            str(root),
            "--plugin",
            str(PLUGIN),
            "--logs",
            str(logs),
        ],
    )
    assert main() == 1
    assert not (logs / "review.html").exists()


def test_harbor_discovery_contract_tracks_packaged_review_tools() -> None:
    from auto_bean.server import list_tools
    from evals.harbor.probe_plugin import EXPECTED_MCP_TOOLS

    tools = {tool.name: tool for tool in asyncio.run(list_tools())}
    assert set(tools) == EXPECTED_MCP_TOOLS
    assert "export_import_review" in EXPECTED_MCP_TOOLS
    assert tools["update_import_review"].meta["ui"]["visibility"] == ["app"]


@pytest.mark.parametrize("subject", ["account", "transaction", "statement"])
def test_inline_unresolved_input_rejects_review(
    reviewed: tuple[Path, Path, dict[str, Any]], subject: str
) -> None:
    root, evidence, expected = reviewed
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    if subject == "account":
        decision = account_decisions(doc)["checking"]
    elif subject == "transaction":
        decision = transaction_decisions(doc)["C-001"]
    else:
        decision = doc["review"]["processing"]
    if subject == "statement":
        decision["needs_input"] = True
    else:
        decision["state"] = "needs_input"
    decision.update(suggestions=["Confirm source evidence"], answer="Already answered")
    write_json(path, doc)
    with pytest.raises(AssertionError, match="Unresolved|Held"):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_independent_inline_material_hash_matches_runtime(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    from auto_bean.review import material

    root, _, _ = reviewed
    doc = read_fixture(root / "statements/parsed/january.json")
    original = material_hash(doc)
    assert original == material(doc)
    doc["review"]["processing"]["attempts"] += 1
    assert material_hash(doc) == original
    for key, value in (
        ("needs_input", False),
        ("suggestions", ["Confirm evidence"]),
        ("answer", "Confirmed"),
    ):
        doc["review"]["processing"][key] = value
        assert material_hash(doc) == material(doc)
        assert material_hash(doc) != original


def delegated_transfer(root: Path, evidence: Path) -> None:
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path, "statements/raw/savings.pdf")
    transaction_decisions(doc)["XFER-001"]["postings"] = []
    write_json(path, doc)
    write_json(evidence / "review.json", checkpoint(root))


@pytest.mark.parametrize(
    "defect", ["missing", "digest", "stage", "validation", "balance", "ledger_hashes"]
)
def test_current_written_validation_is_required(
    reviewed: tuple[Path, Path, dict[str, Any]], defect: str
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    if defect == "missing":
        doc["review"].pop("validation")
    elif defect == "digest":
        doc["review"]["validation"]["digest"] = "0" * 64
    elif defect == "stage":
        doc["review"]["validation"]["stage"] = "review"
    elif defect == "validation":
        doc["review"]["validation"]["state"] = "failed"
    elif defect == "balance":
        doc["review"]["validation"]["balances"] = []
    else:
        doc["review"]["validation"]["ledger_hashes"] = {}
    write_json(path, doc)
    with pytest.raises((AssertionError, WorkflowError)):
        import_checks(root, PLUGIN, evidence, expected, "approve")


@pytest.mark.parametrize(
    "defect",
    ["missing", "duplicate", "double-transfer", "category", "amount", "provenance"],
)
def test_independent_financial_checks_reject_wrong_results(
    reviewed: tuple[Path, Path, dict[str, Any]], defect: str
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    path = root / "beancount/imports.beancount"
    text = path.read_text()
    blocks = text.strip().split("\n\n")
    if defect == "missing":
        text = "\n\n".join(blocks[1:]) + "\n"
    elif defect == "duplicate":
        text += blocks[0] + "\n"
    elif defect == "double-transfer":
        text += blocks[1] + "\n"
    elif defect == "category":
        text = text.replace("Expenses:Food", "Expenses:Bank-Fees")
    elif defect == "amount":
        text = text.replace("-25.00", "-24.00").replace(" 25.00", " 24.00")
    else:
        text = text.replace('record_id: "C-001"', 'record_id: "wrong"')
    path.write_text(text)
    docs = json.loads((evidence / "review.json").read_text())["documents"]
    with pytest.raises(AssertionError):
        financial_checks(root, docs)
    with pytest.raises(AssertionError):
        import_checks(root, PLUGIN, evidence, expected, "approve")


@pytest.mark.parametrize(
    "directive",
    ["1970-01-01 open Expenses:Unexpected EUR\n", "2026-01-31 price USD 0.9 EUR\n"],
)
def test_unrequested_accounts_and_prices_fail(
    reviewed: tuple[Path, Path, dict[str, Any]], directive: str
) -> None:
    root, evidence, _ = reviewed
    complete(root, evidence)
    path = root / "beancount/imports.beancount"
    path.write_text(path.read_text() + directive)
    docs = json.loads((evidence / "review.json").read_text())["documents"]
    with pytest.raises(AssertionError, match="account definitions|price directives"):
        financial_checks(root, docs)


def test_checkpoint_prevents_redefining_reviewed_transactions(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    transaction_decisions(doc)["C-001"]["rationale"] = "Different reviewed explanation"
    write_json(path, doc)
    with pytest.raises(AssertionError, match="changed after review"):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_human_correction_requires_separate_approval(tmp_path: Path) -> None:
    raw_inputs(tmp_path / "raw")
    root, evidence = tmp_path / "ledger", tmp_path / "evidence"
    expected = import_ledger(root, PLUGIN, tmp_path / "raw")
    draft(root, PLUGIN, extract=False, defer=True)
    write_json(evidence / "runtime.json", {"validated": True, "runtime_present": True})
    (evidence / "last-response.txt").write_text(
        "## Import Status: Needs Your Input\n\n**Next Step:** Resolve suggestions.\n"
    )
    scenario_checks(root, evidence, expected, "needs-input")
    reference["correct"](root)
    write_json(evidence / "review.json", checkpoint(root))
    (evidence / "last-response.txt").write_text(
        "checking.csv and savings.pdf\n\n## Import Status: Ready For Review\n\n**Next Step:** Approve transactions.\n"
    )
    import_checks(root, PLUGIN, evidence, expected, "review", explicit_group=False)
    correction_checks(root)
    doc = read_fixture(root / "statements/parsed/january.json")
    transaction_decisions(doc)["C-001"]["answer"] = "Example Market is Expenses:Food."
    savings = read_fixture(
        root / "statements/parsed/january.json", "statements/raw/savings.pdf"
    )
    savings["statement_metadata"]["accounts"][0]["review"]["answer"] = (
        "SAVINGS-TEST maps to Assets:Savings."
    )
    write_json(root / "statements/parsed/january.json", savings)
    write_json(root / "statements/parsed/january.json", doc)
    correction_checks(root)
    postings = transaction_decisions(doc)["C-001"]["postings"]
    food_posting = next(p for p in postings if p["account"] == "Expenses:Food")
    food_posting["account"] = "Expenses:Bank-Fees"
    write_json(root / "statements/parsed/january.json", doc)
    with pytest.raises(AssertionError, match="Wrong corrected transaction category"):
        correction_checks(root)
    food_posting["account"] = "Expenses:Food"
    transaction_decisions(doc)["C-001"]["answer"] = "   "
    write_json(root / "statements/parsed/january.json", doc)
    with pytest.raises(WorkflowError, match="nonempty text"):
        correction_checks(root)
    transaction_decisions(doc)["C-001"].pop("answer")
    write_json(root / "statements/parsed/january.json", doc)
    with pytest.raises(AssertionError, match="human answer"):
        correction_checks(root)


def test_stale_review_preserves_intervening_decision(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    transaction_decisions(doc)["C-001"]["rationale"] = STALE_RATIONALE
    write_json(path, doc)
    reference["stale"](root, evidence / "review.json")
    scenario_checks(root, evidence, expected, "stale")
    doc["review"]["approval"] = {
        "digest": "0" * 64,
        "origin": "panel",
        "approved_at": "2026-01-31T12:00:00Z",
    }
    write_json(path, doc)
    with pytest.raises((AssertionError, WorkflowError)):
        scenario_checks(root, evidence, expected, "stale")


@pytest.mark.parametrize(
    "defect", ["missing_postings", "wrong_postings", "missing_link", "wrong_link"]
)
def test_transfer_requires_reciprocal_owner(
    reviewed: tuple[Path, Path, dict[str, Any]], defect: str
) -> None:
    root, evidence, expected = reviewed
    delegated_transfer(root, evidence)
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    decision = transaction_decisions(doc)["XFER-001"]
    if defect == "missing_postings":
        decision["postings"] = []
    elif defect == "wrong_postings":
        decision["postings"][0]["amount"] = "-101"
    elif defect == "missing_link":
        decision["linked_records"] = []
    else:
        decision["linked_records"][0]["record_id"] = "S-002"
    write_json(path, doc)
    with pytest.raises((AssertionError, WorkflowError)):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_obsolete_execution_artifacts_are_rejected(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    path = root / ".auto-bean/import-sessions/harbor-import.json"
    doc = read_fixture(path)
    doc["changes"] = []
    doc["actions"] = []
    write_json(path, doc)
    with pytest.raises(WorkflowError):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_interrupted_write_cannot_report_completion(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    path = root / "beancount/imports.beancount"
    path.write_text("\n\n".join(path.read_text().split("\n\n")[:2]) + "\n")
    with pytest.raises(AssertionError):
        import_checks(root, PLUGIN, evidence, expected, "approve")


def test_approval_replay_does_not_duplicate_writes(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    before = (root / "beancount/imports.beancount").read_bytes()
    approve(root, evidence / "review.json")
    assert (root / "beancount/imports.beancount").read_bytes() == before
    import_checks(root, PLUGIN, evidence, expected, "approve")


def test_posting_level_transfer_provenance_is_checked_as_a_complete_identity(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, _ = reviewed
    complete(root, evidence)
    path = root / "beancount/imports.beancount"
    text = path.read_text()
    metadata = "\n".join(
        line.replace("  peer_", "    ")
        for line in text.splitlines()
        if line.startswith("  peer_")
    )
    text = (
        "\n".join(line for line in text.splitlines() if not line.startswith("  peer_"))
        + "\n"
    )
    text = text.replace(
        "  Assets:Savings 100.00 EUR\n",
        "  Assets:Savings 100.00 EUR\n" + metadata + "\n",
    )
    path.write_text(text)
    docs = json.loads((evidence / "review.json").read_text())["documents"]
    financial_checks(root, docs)
    path.write_text(
        text.replace('    account_id: "savings"', '    unrelated_note: "savings"')
    )
    with pytest.raises(AssertionError, match="provenance"):
        financial_checks(root, docs)


def test_written_validation_cannot_predate_review(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    doc["review"]["validation"]["checked_at"] = "2020-01-01T00:00:00Z"
    write_json(path, doc)
    with pytest.raises(AssertionError, match="predates review"):
        import_checks(root, PLUGIN, evidence, expected, "approve")


def test_fabricated_panel_approval_is_not_chat_authorization(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    assert "approval" not in doc["review"]
    doc["review"]["approval"] = {
        "digest": material_hash(doc),
        "origin": "panel",
        "approved_at": doc["review"]["validation"]["checked_at"],
    }
    write_json(path, doc)
    with pytest.raises(AssertionError, match="Fabricated panel approval"):
        import_checks(root, PLUGIN, evidence, expected, "approve")


def test_direct_edit_after_review_cannot_use_prior_chat_approval(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, _ = reviewed
    before = (root / "ledger.beancount").read_bytes()
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    transaction_decisions(doc)["C-001"]["rationale"] = "Changed after review"
    write_json(path, doc)
    with pytest.raises(AssertionError, match="changed"):
        approve(root, evidence / "review.json")
    assert (root / "ledger.beancount").read_bytes() == before
    assert not (root / "beancount/imports.beancount").exists()


def test_review_validation_is_allowed_without_certifying_writes(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    from auto_bean.reconciliation import validate_import

    root, evidence, expected = reviewed
    result = validate_import(root, "harbor-import", stage="review")
    assert result["state"] == "passed", result
    import_checks(root, PLUGIN, evidence, expected, "review")
    assert not (root / "beancount/imports.beancount").exists()


@pytest.mark.parametrize("artifact", ["session", "statement"])
def test_revision_bookkeeping_is_not_part_of_agent_artifacts(
    reviewed: tuple[Path, Path, dict[str, Any]],
    artifact: str,
) -> None:
    root, evidence, expected = reviewed
    path = root / (
        ".auto-bean/import-sessions/harbor-import.json"
        if artifact == "session"
        else "statements/parsed/january.json"
    )
    doc = read_fixture(path)
    doc["revision"] = 1
    write_json(path, doc)
    with pytest.raises(WorkflowError):
        import_checks(root, PLUGIN, evidence, expected, "review")


@pytest.mark.parametrize(
    "policy,has_trace,wanted",
    [
        ("required", True, 0),
        ("required", False, 1),
        ("state-only", False, 0),
    ],
)
@pytest.mark.parametrize("diagnostic_reads", [True, False])
def test_trace_and_state_joint_reward(
    reviewed: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
    has_trace: bool,
    wanted: int,
    diagnostic_reads: bool,
) -> None:
    from evals.harbor.verify import main
    from evals.harbor.tests.test_trace import passing_events, save, save_group_workers

    root, evidence, expected = reviewed
    logs, agent_logs = tmp_path / "verifier", tmp_path / "agent"
    baseline = tmp_path / "expected.json"
    write_json(baseline, expected)
    if has_trace:
        events = passing_events("review")
        if not diagnostic_reads:
            # Keep required ledger reads and commands; omit routine references.
            events = events[2:]
        save(agent_logs, events)
        save_group_workers(agent_logs)
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify.py",
            "review",
            "--ledger",
            str(root),
            "--plugin",
            str(PLUGIN),
            "--expected",
            str(baseline),
            "--evidence",
            str(evidence),
            "--logs",
            str(logs),
            "--agent-logs",
            str(agent_logs),
            "--trace-policy",
            policy,
        ],
    )
    assert main() == wanted
    report = json.loads((logs / "report.json").read_text())
    assert report["state_passed"]
    assert report["trace_passed"] == has_trace
    assert report["trace_policy"] == policy
    assert (logs / "reward.txt").read_text().strip() == str(1 - wanted)
    rewards = json.loads((logs / "reward.json").read_text())
    assert rewards == {"reward": 1 - wanted, "state": 1, "trace": int(has_trace)}
    from harbor.trial.multi_step import MultiStepTrial

    assert MultiStepTrial._min_reward_failure(rewards, {"state": 1.0}) is None
    assert (logs / "trace-report.json").is_file()
    assert (logs / "report.md").is_file()
    assert report["schema_version"] == 3
    assert report["check_summary"]["state"]["passed"] > 0
    assert report["check_summary"]["state"]["failed"] == 0
    assert report["check_summary"]["state"]["error"] == 0
    assert report["check_summary"]["trace"]["error"] == (0 if has_trace else 1)
    if has_trace and not diagnostic_reads:
        assert report["check_summary"]["trace"]["diagnostic"] > 0
        assert report["check_summary"]["trace"]["failed"] == 0
        assert "Diagnostic" in (logs / "report.md").read_text()


@pytest.mark.parametrize("error", [False, True])
def test_report_preserves_passes_and_marks_unexecuted_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: bool
) -> None:
    from evals.harbor import verify

    def failing_checks(root: Path, plugin: Path, evidence: Path) -> None:
        verify.require(True, "First requirement failed")
        if error:
            raise ValueError("Invalid schema <value> | detail")
        verify.require(False, "Second requirement failed")
        verify.require(True, "Unreachable requirement")

    logs = tmp_path / "logs"
    monkeypatch.setattr(verify, "init_checks", failing_checks)
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify.py",
            "init",
            "--ledger",
            str(tmp_path),
            "--plugin",
            str(PLUGIN),
            "--logs",
            str(logs),
            "--agent-logs",
            str(tmp_path / "missing-trace"),
        ],
    )
    assert verify.main() == 1
    report = json.loads((logs / "report.json").read_text())
    checks = [check for check in report["checks"] if check["scope"] == "state"]
    assert [check["status"] for check in checks] == [
        "passed",
        "error" if error else "failed",
        "skipped",
    ]
    assert checks[1]["location"]["function"] == "failing_checks"
    assert checks[1]["location"]["line"] > 0
    assert "Unreachable requirement" not in json.dumps(report)
    assert report["check_summary"]["trace"]["error"] == 1
    assert (logs / "reward.txt").read_text() == "0\n"
    rewards = json.loads((logs / "reward.json").read_text())
    from harbor.trial.multi_step import MultiStepTrial

    assert rewards["state"] == 0
    assert MultiStepTrial._min_reward_failure(rewards, {"state": 1.0}) is not None
    text = (logs / "report.md").read_text()
    assert "First requirement failed" in text
    assert "Remaining state checks" in text
    if error:
        assert "\\| detail" in text
    # The context-local recorder must not leak into later direct checks.
    assert verify._STATE_CHECKS.get() is None


def test_markdown_report_is_deterministic_and_escapes_input(tmp_path: Path) -> None:
    from evals.harbor.verify import (
        finish_report,
        write_report_markdown,
    )

    checks = [
        {"scope": "state", "status": "passed", "failure_message": "Good check"},
        {
            "scope": "state",
            "status": "failed",
            "failure_message": '<script> & "quoted"',
        },
        {
            "scope": "state",
            "status": "skipped",
            "requirement": "Remaining state checks",
        },
    ]
    report: dict[str, Any] = {
        "phase": "review",
        "passed": False,
        "trace_policy": "required",
    }
    finish_report(
        report,
        checks,
        {"checks": [{"requirement": f"trace:{i}", "passed": False} for i in range(14)]},
    )
    md = tmp_path / "report.md"
    write_report_markdown(md, report)
    first = md.read_bytes()
    write_report_markdown(md, report)
    assert md.read_bytes() == first
    for scope, counts in report["check_summary"].items():
        assert (
            f"| {scope} | {counts['passed']} | {counts['failed']} | "
            f"{counts['error']} | {counts['skipped']} |"
        ) in md.read_text()
    markdown = md.read_text()
    assert markdown.index("❌ Failed") < markdown.index("✅ Passed")
    assert "&lt;script&gt;" in markdown


def test_explicit_group_cannot_be_replaced_by_inferred_groups(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    path = root / ".auto-bean/import-sessions/harbor-import.json"
    session = read_fixture(path)
    session["groups"][0]["origin"] = "agent"
    write_json(path, session)
    with pytest.raises(AssertionError, match="Explicit January accounts group"):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_group_ids_are_preserved_across_approval(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    path = root / ".auto-bean/import-sessions/harbor-import.json"
    session = read_fixture(path)
    session["groups"][0]["group_id"] = "changed"
    write_json(path, session)
    with pytest.raises(WorkflowError, match="group membership"):
        import_checks(root, PLUGIN, evidence, expected, "approve")


@pytest.mark.parametrize("closing_assertion", [False, True])
def test_review_accepts_source_documents_and_exact_closing_assertions(
    reviewed: tuple[Path, Path, dict[str, Any]], closing_assertion: bool
) -> None:
    root, evidence, expected = reviewed
    path = root / "statements/parsed/january.json"
    if closing_assertion:
        for raw, account, amount in (
            ("statements/raw/checking.csv", "checking", "870"),
            ("statements/raw/savings.pdf", "savings", "602"),
        ):
            doc = read_fixture(path, raw)
            account_decisions(doc)[account]["proposed_directives"].append(
                f"2026-02-01 balance Assets:{account.title()} {amount} EUR"
            )
            write_json(path, doc)
    write_json(evidence / "review.json", checkpoint(root))
    import_checks(root, PLUGIN, evidence, expected, "review")
    assert not (root / "beancount/imports.beancount").exists()


@pytest.mark.parametrize(
    "directives",
    [
        [],
        ['2026-01-31 document Assets:Savings "statements/raw/checking.csv"'],
        ['2026-01-30 document Assets:Checking "statements/raw/checking.csv"'],
        ['2026-01-31 document Assets:Checking "statements/raw/savings.pdf"'],
        ['2026-01-31 document Assets:Checking "../../outside.csv"'],
        ["2026-01-01 open Assets:Invented EUR"],
        [
            '2026-01-31 document Assets:Checking "statements/raw/checking.csv"\nplugin "evil"'
        ],
        ['2026-01-31 document Assets:Checking "statements/raw/checking.csv"'] * 2,
        ["2026-02-01 balance Assets:Checking 999 EUR"],
        ["2026-01-31 balance Assets:Checking 870 EUR"],
        ["2026-02-01 balance Assets:Checking 870 USD"],
        ["2026-02-01 balance Assets:Checking 870 ~ 100 EUR"],
    ],
)
def test_unsupported_directives_still_fail(
    reviewed: tuple[Path, Path, dict[str, Any]], directives: list[str]
) -> None:
    root, evidence, expected = reviewed
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    account_decisions(doc)["checking"]["proposed_directives"] = directives
    write_json(path, doc)
    write_json(evidence / "review.json", checkpoint(root))
    with pytest.raises(AssertionError):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_written_ledger_must_contain_reviewed_document_directives(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, _ = reviewed
    complete(root, evidence)
    docs = json.loads((evidence / "review.json").read_text())["documents"]
    financial_checks(root, docs)
    ledger = root / "beancount/imports.beancount"
    ledger.write_text(
        "\n".join(
            line for line in ledger.read_text().splitlines() if " document " not in line
        )
    )
    with pytest.raises(AssertionError, match="supporting directives"):
        financial_checks(root, docs)


@pytest.mark.parametrize(
    "defect", [None, "written", "digest", "success", "empty_errors", "hashes"]
)
def test_needs_input_accepts_failed_current_review_only(
    tmp_path: Path, defect: str | None
) -> None:
    from auto_bean.reconciliation import validate_import

    raw_inputs(tmp_path / "raw")
    root, evidence = tmp_path / "ledger", tmp_path / "evidence"
    expected = import_ledger(root, PLUGIN, tmp_path / "raw")
    draft(root, PLUGIN, extract=False, defer=True)
    result = validate_import(root, "harbor-import", stage="review")
    assert result["state"] == "failed"
    path = root / "statements/parsed/january.json"
    doc = read_fixture(path)
    validation = doc["review"]["validation"]
    if defect == "written":
        validation["stage"] = "written"
    elif defect == "digest":
        validation["digest"] = "0" * 64
    elif defect == "success":
        validation["state"] = "passed"
    elif defect == "empty_errors":
        validation["errors"] = []
    elif defect == "hashes":
        validation["ledger_hashes"] = expected["financial_hashes"]
    write_json(path, doc)
    write_json(evidence / "runtime.json", {"validated": True, "runtime_present": True})
    (evidence / "last-response.txt").write_text(
        "## Import Status: Needs Your Input\n\n**Next Step:** Resolve suggestions.\n"
    )
    if defect:
        with pytest.raises(AssertionError):
            scenario_checks(root, evidence, expected, "needs-input")
    else:
        scenario_checks(root, evidence, expected, "needs-input")


def test_extracted_account_ids_need_not_match_oracle_ids(tmp_path: Path) -> None:
    raw_inputs(tmp_path / "raw")
    root, evidence = tmp_path / "ledger", tmp_path / "evidence"
    expected = import_ledger(root, PLUGIN, tmp_path / "raw")
    draft(root, PLUGIN, extract=False, defer=True)
    path = root / "statements/parsed/january.json"

    def rename_accounts() -> None:
        group = json.loads(path.read_text())
        for doc in group["statements"]:
            for account in doc["statement_metadata"]["accounts"]:
                account["account_id"] = account["account_id"].upper() + "-TEST"
            for row in doc["extracted_records"]:
                row["account_id"] = row["account_id"].upper() + "-TEST"
                for link in row["review"].get("linked_records", []):
                    link["account_id"] = link["account_id"].upper() + "-TEST"
        write_json(path, group)

    original = path.read_text()
    rename_accounts()
    write_json(evidence / "runtime.json", {"validated": True, "runtime_present": True})
    (evidence / "last-response.txt").write_text(
        "## Import Status: Needs Your Input\n\n**Next Step:** Resolve suggestions.\n"
    )
    scenario_checks(root, evidence, expected, "needs-input")
    # The oracle helper uses its own fixture IDs. Rename its corrected output
    # before grading, just as an extractor may supply source-owned IDs.
    path.write_text(original)
    reference["correct"](root)
    rename_accounts()
    correction_checks(root)
