from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch

from auto_bean.cli import main
from auto_bean.init import CommandResult, EnvironmentInfo, InitService, ProjectPaths


def test_package_foundation_layout_and_entrypoint() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src" / "auto_bean"

    assert src_root.is_dir()
    assert (src_root / "__init__.py").is_file()
    assert (src_root / "__main__.py").is_file()

    assert (src_root / "init.py").is_file()
    assert (src_root / "smoke.py").is_file()
    assert (src_root / "cli.py").is_file()

    from auto_bean import main as entrypoint

    assert callable(entrypoint)


def test_resource_assets_exist_under_repo_roots() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    assert repo_root.joinpath("skill_sources", "auto-bean-apply", "SKILL.md").is_file()
    assert repo_root.joinpath("skill_sources", "auto-bean-import", "SKILL.md").is_file()
    assert repo_root.joinpath(
        "skill_sources", "shared", "mutation-pipeline.md"
    ).is_file()
    assert repo_root.joinpath("workspace_template", "AGENTS.md").is_file()


@dataclass
class FakePlatformProbe:
    environment: EnvironmentInfo

    def inspect(self) -> EnvironmentInfo:
        return self.environment


@dataclass
class FakeToolProbe:
    available_tools: dict[str, str]

    def find(self, command: str) -> str | None:
        return self.available_tools.get(command)


@dataclass
class FakeCommandRunner:
    responses: dict[tuple[str, ...], CommandResult]
    calls: list[tuple[str, ...]] | None = None

    def run(self, args: Sequence[str], cwd: Path | None = None) -> CommandResult:
        if self.calls is not None:
            self.calls.append(tuple(args))
        if cwd is not None and tuple(args[:2]) == ("/usr/bin/git", "init"):
            (cwd / ".git").mkdir(parents=True, exist_ok=True)
        if cwd is not None and tuple(args[:2]) == ("/opt/homebrew/bin/uv", "venv"):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        if cwd is not None and tuple(args[:3]) == (
            "/opt/homebrew/bin/uv",
            "pip",
            "install",
        ):
            (cwd / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
            (cwd / ".venv" / "bin" / "bean-check").write_text("", encoding="utf-8")
            (cwd / ".venv" / "bin" / "fava").write_text("", encoding="utf-8")
            (cwd / ".venv" / "bin" / "docling").write_text("", encoding="utf-8")
        return self.responses.get(tuple(args), CommandResult(returncode=0))


def seed_story_2_1_assets(tmp_path: Path) -> None:
    template_root = tmp_path / "workspace_template"
    (template_root / "beancount").mkdir(parents=True)
    (template_root / ".agents").mkdir(parents=True)
    (template_root / "statements" / "raw").mkdir(parents=True)
    (template_root / "statements" / "parsed").mkdir(parents=True)
    (template_root / ".auto-bean" / "artifacts").mkdir(parents=True)
    (template_root / ".auto-bean" / "proposals").mkdir(parents=True)
    (template_root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (template_root / "ledger.beancount").write_text(
        'option "title" "Test Ledger"\ninclude "beancount/opening-balances.beancount"\n',
        encoding="utf-8",
    )
    (template_root / "beancount" / "opening-balances.beancount").write_text(
        "1970-01-01 open Assets:Checking EUR\n1970-01-01 open Equity:Opening-Balances EUR\n",
        encoding="utf-8",
    )
    (template_root / "statements" / "parsed" / ".gitkeep").write_text(
        "", encoding="utf-8"
    )
    (template_root / "statements" / "import-status.yml").write_text(
        "version: 1\nstatements: {}\n",
        encoding="utf-8",
    )

    skill_sources_root = tmp_path / "skill_sources"
    (skill_sources_root / "auto-bean-apply" / "scripts").mkdir(parents=True)
    (skill_sources_root / "auto-bean-apply" / "agents").mkdir(parents=True)
    (skill_sources_root / "auto-bean-import" / "agents").mkdir(parents=True)
    (skill_sources_root / "auto-bean-import" / "references").mkdir(parents=True)
    (skill_sources_root / "shared").mkdir(parents=True)
    (skill_sources_root / "auto-bean-apply" / "SKILL.md").write_text(
        "# Apply\n", encoding="utf-8"
    )
    (skill_sources_root / "auto-bean-apply" / "agents" / "openai.yaml").write_text(
        'interface:\n  display_name: "Apply"\n  short_description: "Apply changes"\n  default_prompt: "Use $auto-bean-apply."\n',
        encoding="utf-8",
    )
    (skill_sources_root / "auto-bean-import" / "SKILL.md").write_text(
        "# Import\n", encoding="utf-8"
    )
    (skill_sources_root / "auto-bean-import" / "agents" / "openai.yaml").write_text(
        'interface:\n  display_name: "Import"\n  short_description: "Import statements"\n  default_prompt: "Use $auto-bean-import."\n',
        encoding="utf-8",
    )
    (
        skill_sources_root
        / "auto-bean-import"
        / "references"
        / "parsed-statement-output.example.json"
    ).write_text(
        '{"parse_run_id": "demo", "source_file": "statements/raw/demo.pdf", "source_fingerprint": "sha256:demo", "source_format": "pdf", "parser": {"name": "docling"}, "parse_status": "parsed", "parsed_at": "2026-04-11T09:00:00Z", "warnings": [], "blocking_issues": [], "extracted_records": []}\n',
        encoding="utf-8",
    )
    (
        skill_sources_root
        / "auto-bean-import"
        / "references"
        / "import-status.example.yml"
    ).write_text(
        "version: 1\nstatements: {}\n",
        encoding="utf-8",
    )
    (skill_sources_root / "shared" / "mutation-pipeline.md").write_text(
        "# Pipeline\n", encoding="utf-8"
    )
    (skill_sources_root / "shared" / "mutation-authority-matrix.md").write_text(
        "# Authority\n", encoding="utf-8"
    )


def make_service(
    tmp_path: Path,
    *,
    system: str = "Darwin",
    tools: dict[str, str] | None = None,
    responses: dict[tuple[str, ...], CommandResult] | None = None,
    calls: list[tuple[str, ...]] | None = None,
    prompt: Callable[[str], str] | None = None,
) -> InitService:
    repo_root = tmp_path
    (repo_root / "src").mkdir(exist_ok=True)
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "auto-bean"',
                'version = "0.1.0"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    return InitService(
        paths=ProjectPaths(start=repo_root),
        platform=FakePlatformProbe(
            EnvironmentInfo(
                system=system,
                release="24.0.0",
                machine="arm64",
                python_version="3.13.0",
            )
        ),
        tools=FakeToolProbe(
            tools
            if tools is not None
            else {
                "git": "/usr/bin/git",
                "uv": "/opt/homebrew/bin/uv",
            }
        ),
        commands=FakeCommandRunner(
            responses if responses is not None else {}, calls=calls
        ),
        prompt=prompt or (lambda _: "Codex"),
    )


def test_init_fails_on_unsupported_os(tmp_path: Path) -> None:
    service = make_service(tmp_path, system="Linux")

    result = service.init("demo-ledger")

    assert result.status == "failed"
    assert result.error_code == "unsupported_environment"
    assert result.checks[0].details["detected_system"] == "Linux"


def test_init_reports_missing_uv_prerequisite(tmp_path: Path) -> None:
    seed_story_2_1_assets(tmp_path)
    service = make_service(tmp_path, tools={})

    result = service.init("demo-ledger")

    assert result.status == "failed"
    assert result.error_code == "missing_uv"
    remediation = result.details["remediation"]
    assert isinstance(remediation, str)
    assert "uv tool install --from . --force auto-bean" in remediation


def test_init_is_reserved_for_later_workspace_story(tmp_path: Path) -> None:
    project_name = f"demo-ledger-{tmp_path.name[-6:]}"
    seed_story_2_1_assets(tmp_path)
    service = make_service(tmp_path)

    result = service.init(project_name)

    assert result.status == "ok"
    assert result.error_code is None
    assert result.details["project_name"] == project_name


def test_cli_renders_json_failure_output(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    service = make_service(tmp_path, system="Linux")
    monkeypatch.setattr("auto_bean.cli.build_init_service", lambda: service)

    exit_code = main(["init", "demo-ledger", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["status"] == "failed"
    assert payload["error_code"] == "unsupported_environment"
