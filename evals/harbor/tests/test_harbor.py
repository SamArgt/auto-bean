from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import runpy
from pathlib import Path, PurePosixPath
from typing import Any
from unittest.mock import AsyncMock

import pytest
import yaml

from auto_bean import init
from evals.harbor.adapter import AutoBeanCodex
from evals.harbor.fixtures import import_ledger, raw_inputs, sha256, write_json

from evals.harbor.capture import metadata
from evals.harbor.verify import import_checks, init_checks

PLUGIN = Path(__file__).resolve().parents[3] / "plugins/auto-bean"
reference = runpy.run_path(
    str(
        PLUGIN.parents[1]
        / "evals/harbor/tasks/import-two-statements/solution/reference.py"
    )
)
approve, draft = reference["approve"], reference["draft"]


@pytest.fixture
def reviewed(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    raw_inputs(tmp_path / "raw")
    root = tmp_path / "ledger"
    expected = import_ledger(root, PLUGIN, tmp_path / "raw")
    draft(root, PLUGIN, extract=False)
    evidence = tmp_path / "evidence"
    write_json(evidence / "runtime.json", {"validated": True, "runtime_present": True})
    write_json(
        evidence / "review.json",
        {
            "financial_hashes": {
                path.relative_to(root).as_posix(): sha256(path)
                for path in root.rglob("*.beancount")
            },
            "status": (root / "statements/import-status.yml").read_text(),
        },
    )
    (evidence / "last-response.txt").write_text(
        "checking.csv and savings.pdf reconciled; bean-check passed.\n\n---\n\n"
        "## Import Status: Ready For Review\n\n**Summary:** Both statements reviewed.\n**Next Step:** Approve the candidates.\n"
    )
    return root, evidence, expected


def complete(root: Path, evidence: Path) -> None:
    approve(root)
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


def test_memory_outcomes_use_the_product_import_artifact_contract(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    shutil.rmtree(root / ".auto-bean/artifacts/memory")
    for path in (root / ".auto-bean/artifacts/import").glob("*.md"):
        with path.open("a") as stream:
            stream.write(
                "\n## Memory Attribution\nNo prior memory used.\n## Memory Candidates\nNo new eligible decisions; handoff has no writes.\n"
            )
    complete(root, evidence)
    import_checks(root, PLUGIN, evidence, expected, "approve")


def test_shared_transfer_accepts_posting_level_provenance(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    path = root / "beancount/imports.beancount"
    old_hash = sha256(path)
    text = (
        "\n".join(
            line
            for line in path.read_text().splitlines()
            if not line.startswith("  paired_")
        )
        + "\n"
    )
    text = text.replace(
        "  Assets:Savings 100 EUR\n",
        '  Assets:Savings 100 EUR\n    source_fingerprint: "sha256:'
        + sha256(root / "statements/raw/savings.pdf")
        + '"\n    account_id: "savings"\n    record_id: "XFER-001"\n',
    )
    path.write_text(text)
    for artifact in (root / ".auto-bean/artifacts/import").glob("*.md"):
        artifact.write_text(artifact.read_text().replace(old_hash, sha256(path)))
    import_checks(root, PLUGIN, evidence, expected, "review")


def test_epilogues_are_required_at_completion_not_before_user_approval(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    shutil.rmtree(root / ".auto-bean/artifacts/prices")
    shutil.rmtree(root / ".auto-bean/artifacts/memory")
    import_checks(root, PLUGIN, evidence, expected, "review")
    complete(root, evidence)
    with pytest.raises(AssertionError, match="prices stage"):
        import_checks(root, PLUGIN, evidence, expected, "approve")
    price = root / ".auto-bean/artifacts/prices/outcome.md"
    price.parent.mkdir()
    price.write_text("No eligible prices; zero jobs; no follow-ups.\n")
    with pytest.raises(AssertionError, match="memory handoff"):
        import_checks(root, PLUGIN, evidence, expected, "approve")


@pytest.mark.parametrize(
    "defect",
    ["missing", "duplicate", "double-transfer", "category", "amount", "provenance"],
)
def test_rejects_wrong_financial_results(
    reviewed: tuple[Path, Path, dict[str, Any]], defect: str
) -> None:
    root, evidence, expected = reviewed
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
        text = text.replace("-25 EUR", "-24 EUR").replace("25 EUR", "24 EUR")
    else:
        text = (
            "\n".join(
                line
                for line in text.splitlines()
                if "paired_source_fingerprint" not in line
            )
            + "\n"
        )
    path.write_text(text)
    with pytest.raises(AssertionError):
        import_checks(root, PLUGIN, evidence, expected, "review")


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


def test_missing_approval_fails(reviewed: tuple[Path, Path, dict[str, Any]]) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    for path in (root / ".auto-bean/artifacts/import").glob("*.md"):
        path.write_text(path.read_text().split("Explicit approval:")[0])
    with pytest.raises(AssertionError, match="approval evidence"):
        import_checks(root, PLUGIN, evidence, expected, "approve")


def test_raw_changes_fail(reviewed: tuple[Path, Path, dict[str, Any]]) -> None:
    root, evidence, expected = reviewed
    (root / "statements/raw/checking.csv").write_text("tampered source")
    with pytest.raises(AssertionError, match="Preserved file changed"):
        import_checks(root, PLUGIN, evidence, expected, "review")


def test_candidate_change_after_review_fails(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    complete(root, evidence)
    path = root / "beancount/imports.beancount"
    old_hash = sha256(path)
    path.write_text(path.read_text() + "; new financial-file edit after review\n")
    for artifact in (root / ".auto-bean/artifacts/import").glob("*.md"):
        artifact.write_text(artifact.read_text().replace(old_hash, sha256(path)))
    with pytest.raises(AssertionError, match="changed the reviewed"):
        import_checks(root, PLUGIN, evidence, expected, "approve")


def test_invalid_parsed_state_fails(
    reviewed: tuple[Path, Path, dict[str, Any]],
) -> None:
    root, evidence, expected = reviewed
    path = root / "statements/parsed/checking.json"
    data = json.loads(path.read_text())
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
        for name in ("init-ledger", "import-two-statements")
    ]
    assert not tasks[0].has_steps
    assert tasks[1].has_steps
    assert tasks[1].config.multi_step_reward_strategy == "final"
    assert tasks[1].config.steps and tasks[1].config.steps[0].min_reward == 1.0
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
        build = yaml.safe_load(compose.read_text())["services"]["main"]["build"]
        context = build["context"].replace("${CONTEXT_DIR}", str(compose.parent))
        assert Path(context).resolve() == root
        assert build["dockerfile"] == "evals/harbor/environment/Dockerfile"
        if compose.parent.name == "tests":
            assert (
                Path(build["args"]["HARBOR_TEST_SCRIPT"])
                == compose.parent.relative_to(root) / "test.sh"
            )
    dockerfile = (suite / "environment/Dockerfile").read_text()
    agent_stages, verifier_stage = dockerfile.split("FROM base AS verifier")
    assert "COPY plugins/auto-bean /opt/" in agent_stages
    assert "COPY evals/harbor/verify.py" not in agent_stages
    assert "reference.py" not in dockerfile
    assert "COPY evals/harbor/verify.py" in verifier_stage
    assert not (suite / "run.py").exists()


def test_native_harbor_config_defaults() -> None:
    from harbor.agents.factory import AgentFactory
    from harbor.models.job.config import JobConfig
    from harbor.models.trial.config import TaskConfig, TrialConfig
    from harbor.viewer.trial_utils import agent_name_from_config

    config = JobConfig.model_validate(
        yaml.safe_load((PLUGIN.parents[1] / "evals/harbor/codex.yaml").read_text())
    )
    assert config.n_attempts == config.n_concurrent_trials == 1
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


def test_fixture_regeneration_overwrites_previous_files(tmp_path: Path) -> None:
    raw, root = tmp_path / "raw", tmp_path / "ledger"
    raw_inputs(raw)
    expected = import_ledger(root, PLUGIN, raw)
    (raw / "checking.csv").write_text("obsolete")
    (raw / "savings.pdf").write_bytes(b"obsolete")
    (root / "obsolete-result.txt").write_text("old trial")
    (root / "ledger.beancount").write_text("invalid old candidate")
    raw_inputs(raw)
    assert import_ledger(root, PLUGIN, raw) == expected
    assert not (root / "obsolete-result.txt").exists()


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


def test_adapter_captures_approval_checkpoint_without_replacing_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from harbor.agents.installed.codex import Codex

    adapter = object.__new__(AutoBeanCodex)
    adapter._resume = True
    adapter.environment_logs_dir = PurePosixPath("/logs/agent")
    run = AsyncMock()
    capture = AsyncMock()
    monkeypatch.setattr(Codex, "run", run)
    monkeypatch.setattr(adapter, "exec_as_agent", capture)
    asyncio.run(adapter.run("approval", object(), object()))
    run.assert_awaited_once()
    assert "--phase approve" in capture.call_args.kwargs["command"]
