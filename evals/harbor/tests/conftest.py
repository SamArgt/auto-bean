"""Keep standalone container helpers importable in local verifier tests."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


@pytest.fixture(autouse=True)
def git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    from evals.harbor.fixtures import IDENTITY

    for key, value in IDENTITY.items():
        monkeypatch.setenv(key, value)
