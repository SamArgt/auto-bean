"""The prototype persists synthetic copies and keeps seed evidence unchanged."""

import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "review_demo", ROOT / "experiments/review-ui-design/serve.py"
)
assert spec and spec.loader
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def store(tmp_path: Path, stage: str = "accounts") -> Any:
    shutil.copytree(
        ROOT / "experiments/review-ui-design/fixtures", tmp_path / "fixtures"
    )
    return demo.DemoStore(stage, tmp_path)


def test_demo_saves_json_preserves_siblings_and_resets(tmp_path: Path) -> None:
    db = store(tmp_path)
    before = db.state()
    statement = before["documents"][0]["statements"][0]
    source = statement["source_file"]
    account = statement["statement_metadata"]["accounts"][0]
    updated = db.save(
        {
            "expected_token": before["batch"]["token"],
            "source_file": source,
            "subject": "account:" + account["account_id"],
            "value": "Assets:Bank:New",
        }
    )
    assert (
        updated["documents"][0]["statements"][0]["statement_metadata"]["accounts"][0][
            "review"
        ]["ledger_account"]
        == "Assets:Bank:New"
    )
    assert (
        updated["documents"][0]["statements"][1:]
        == before["documents"][0]["statements"][1:]
    )
    assert updated["batch"]["notifications"] == 0
    assert "Assets:Bank:New" in updated["batch"]["history"][0]["diff"]
    assert demo.DemoStore("accounts", tmp_path).state() == updated
    seed = json.loads(
        (db.seed / before["session"]["groups"][0]["parsed_group"]).read_text()
    )
    assert seed == before["documents"][0]
    with pytest.raises(ValueError, match="Reload"):
        db.save({"expected_token": before["batch"]["token"], "subject": "source"})
    with pytest.raises(ValueError, match="still need review"):
        db.send({"expected_token": updated["batch"]["token"]})
    reset = db.reset()
    assert reset["documents"] == before["documents"]
    assert reset["batch"]["history"] == []
    assert reset["batch"]["pending"] == {}


def test_demo_batch_after_all_account_inputs(tmp_path: Path) -> None:
    db = store(tmp_path)
    state = db.state()
    for group in state["documents"]:
        for statement in group["statements"]:
            for account in statement["statement_metadata"]["accounts"]:
                if account["review"]["state"] == "needs_input":
                    state = db.save(
                        {
                            "expected_token": state["batch"]["token"],
                            "source_file": statement["source_file"],
                            "subject": "account:" + account["account_id"],
                            "value": "Assets:Bank:Checking",
                        }
                    )
    assert state["batch"]["notifications"] == 0
    sent = db.send({"expected_token": state["batch"]["token"]})
    assert sent["batch"]["notifications"] == 1
    assert not sent["batch"]["pending"]
    assert sent["batch"]["last_sent"]
    assert sent["documents"] == state["documents"]
