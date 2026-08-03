from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRICE_SKILL = ROOT / "skill_sources" / "auto-bean-prices" / "SKILL.md"
RUN_CONTRACT = (
    ROOT / "skill_sources" / "auto-bean-prices" / "references" / "price-run-contract.md"
)
IMPORT_EPILOGUE = (
    ROOT
    / "skill_sources"
    / "auto-bean-import"
    / "references"
    / "import-5-price-update.md"
)


def test_import_epilogue_requires_a_single_dated_snapshot() -> None:
    skill = PRICE_SKILL.read_text(encoding="utf-8")
    epilogue = IMPORT_EPILOGUE.read_text(encoding="utf-8")

    assert "--date <target-date> ledger.beancount" in skill
    assert "do not add `--update`" in skill
    assert "one explicit dated snapshot without `--update`" in epilogue


def test_historical_backfill_requires_explicit_intent_and_dry_run() -> None:
    contract = RUN_CONTRACT.read_text(encoding="utf-8")

    assert "only when the user explicitly requests historical coverage" in contract
    assert "Dry-run the exact `--update` command first" in contract


def test_running_or_empty_initial_output_is_not_completion() -> None:
    contract = RUN_CONTRACT.read_text(encoding="utf-8")

    assert "poll the same session until it exits" in contract
    assert "an initial empty chunk" in contract
    assert "is not a completed command" in contract


def test_zero_directives_require_full_reconciliation() -> None:
    contract = RUN_CONTRACT.read_text(encoding="utf-8")

    assert "every job was explicitly logged as redundant" in contract
    assert "one or more dry-run jobs remain unaccounted for" in contract
    assert "Zero emitted directives alone is not success or failure" in contract


def test_price_artifact_requires_terminal_telemetry() -> None:
    contract = RUN_CONTRACT.read_text(encoding="utf-8")
    required_fields = (
        "fetch mode",
        "dry-run job count",
        "terminal completion state and exit code",
        "start time, end time, and duration",
        "emitted directive count and redundant/ignored count",
        "sanitized stderr summary",
    )

    for field in required_fields:
        assert field in contract
