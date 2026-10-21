from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "plugins" / "auto-bean"
REFERENCE = ROOT / "skills/auto-bean-prices/references/price-reference.md"


def command_examples() -> list[list[list[str]]]:
    return [
        [shlex.split(line) for line in block.strip().splitlines()]
        for block in re.findall(r"```sh\n(.*?)```", REFERENCE.read_text(), re.DOTALL)
    ]


@pytest.mark.parametrize("index", [0, 1], ids=["snapshot", "source-probe"])
def test_price_examples_preserve_preflight_selection_in_live_fetch(index: int) -> None:
    preflight, live = command_examples()[index]
    assert preflight[:2] == live[:2] == ["auto_bean", "bean-price"]
    assert "--dry-run" in preflight and "--dry-run" not in live
    assert "-v" in live and "-v" not in preflight
    assert [part for part in preflight if part != "--dry-run"] == [
        part for part in live if part != "-v"
    ]
    assert preflight[preflight.index("--date") + 1] == "<target-date>"
    if index == 0:
        assert preflight[-1] == "ledger.beancount"
    else:
        assert preflight[preflight.index("-e") + 1] == "<QUOTE>:<SOURCE>/<SYMBOL>"


def test_snapshot_and_probe_examples_do_not_expand_to_historical_backfill() -> None:
    for pair in command_examples():
        for command in pair:
            assert "--update" not in command
            assert not {"--all", "--inactive", "--clobber"}.intersection(command)


def test_documented_import_outcomes_match_the_strict_session_schema() -> None:
    schema = json.loads((ROOT / "references/schemas/session.schema.json").read_text())
    allowed = set(
        schema["properties"]["price_runs"]["items"]["properties"]["state"]["enum"]
    )
    documented = set(re.findall(r"\| Import JSON \| `([^`]+)`", REFERENCE.read_text()))
    assert documented == allowed - {"pending", "running"}
    assert "succeeded" not in documented
