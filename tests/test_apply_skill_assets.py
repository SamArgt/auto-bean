from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_apply_skill_requires_clarification_guidance_checkpoint() -> None:
    skill_path = repo_root() / "skill_sources" / "auto-bean-apply" / "SKILL.md"
    content = skill_path.read_text()

    assert "clarification-guidance.md" in content
    assert "Ask only the minimum bounded questions needed" in content
    assert "Do not ask for commit, push, or final finding decisions" in content


def test_apply_skill_requires_resume_trace_and_fail_closed_behavior() -> None:
    skill_path = repo_root() / "skill_sources" / "auto-bean-apply" / "SKILL.md"
    content = skill_path.read_text()

    assert "Show how the answer changed" in content
    assert (
        "If the user response is still ambiguous, contradictory, or insufficient, fail closed"
        in content
    )
    assert "suggest a targeted update to the source-context memory file" in content
    assert "resulting working-tree mutation" in content
    assert (
        "confirmed validation failures called out separately from inferred risks"
        in content
    )
    assert "reverting the recorded commit" in content


def test_clarification_guidance_stays_simple_and_actionable() -> None:
    guidance_path = (
        repo_root()
        / "skill_sources"
        / "auto-bean-apply"
        / "references"
        / "clarification-guidance.md"
    )
    content = guidance_path.read_text()

    assert "Ask only the minimum bounded questions needed" in content
    assert "After the user answers, update the drafted workspace changes" in content
    assert "suggest an update to the source-context memory file" in content
    assert ".auto-bean/artifacts/clarifications/" not in content
