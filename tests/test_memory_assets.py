from __future__ import annotations

import json
from pathlib import Path

from auto_bean.init import (
    CommandResult,
    InitService,
    PlatformProbe,
    ProjectPaths,
    ToolProbe,
)


def test_memory_skill_and_shared_policy_are_authored() -> None:
    root = Path(__file__).resolve().parents[1]

    assert (root / "skill_sources" / "auto-bean-memory" / "SKILL.md").is_file()
    assert (
        root / "skill_sources" / "auto-bean-memory" / "agents" / "openai.yaml"
    ).is_file()
    assert (root / "skill_sources" / "shared" / "memory-access-rules.md").is_file()
    for reference in memory_reference_map().values():
        assert (root / "skill_sources" / "auto-bean-memory" / reference).is_file()


def test_init_required_assets_include_memory_skill_and_policy() -> None:
    service = InitService(
        paths=ProjectPaths(),
        platform=PlatformProbe(),
        tools=ToolProbe(),
        commands=NoopCommands(),
    )
    root = Path(__file__).resolve().parents[1]

    check = service._check_required_assets(
        name="skill_sources_available",
        details_key="skill_sources_directory",
        error_code="missing_skill_sources",
        message="Authored skill source assets are available.",
        failure_message="Authored skill source assets are missing.",
        root=root / "skill_sources",
        required_paths=(
            "auto-bean-apply/SKILL.md",
            "auto-bean-query/SKILL.md",
            "auto-bean-write/SKILL.md",
            "auto-bean-import/SKILL.md",
            "auto-bean-memory/SKILL.md",
            "auto-bean-memory/references/account-mapping.example.md",
            "auto-bean-memory/references/category-mapping.example.md",
            "auto-bean-memory/references/clarification-outcome.example.md",
            "auto-bean-memory/references/deduplication-decision.example.md",
            "auto-bean-memory/references/import-source-behavior.example.md",
            "auto-bean-memory/references/naming-convention.example.md",
            "auto-bean-memory/references/transfer-detection.example.md",
            "shared/memory-access-rules.md",
        ),
    )

    assert check.status.value == "pass"


def test_scaffold_preserves_existing_memory_files(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    service = InitService(
        paths=ProjectPaths(),
        platform=PlatformProbe(),
        tools=ToolProbe(),
        commands=NoopCommands(),
    )
    target = tmp_path / "workspace"
    existing_memory = target / ".auto-bean" / "memory" / "account_mappings.json"
    existing_memory.parent.mkdir(parents=True)
    existing_memory.write_text(
        '{"schema_version":1,"memory_type":"account_mapping","records":[{"kept":true}]}\n',
        encoding="utf-8",
    )

    created_paths = service._copy_tree(
        source=root / "workspace_template",
        destination=target,
    )

    assert '"kept":true' in existing_memory.read_text(encoding="utf-8")
    assert ".auto-bean/memory/import_sources/.gitkeep" in created_paths
    assert ".auto-bean/memory/import_sources/index.json" in created_paths


def test_non_memory_skills_do_not_claim_direct_memory_write_authority() -> None:
    root = Path(__file__).resolve().parents[1]
    direct_write_phrases = (
        "write memory",
        "write repeated-import source context",
        "write only under `.auto-bean/memory",
    )

    for skill_name in ("auto-bean-import", "auto-bean-apply", "auto-bean-query"):
        text = (root / "skill_sources" / skill_name / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "auto-bean-memory" in text
        for phrase in direct_write_phrases:
            assert phrase not in text


class NoopCommands:
    def run(self, args: object, cwd: Path | None = None) -> CommandResult:
        return CommandResult(returncode=0)


def test_workspace_memory_template_uses_fixed_category_files() -> None:
    root = Path(__file__).resolve().parents[1]
    memory_root = root / "workspace_template" / ".auto-bean" / "memory"
    expected_files = {
        "account_mappings.json": "account_mapping",
        "category_mappings.json": "category_mapping",
        "naming_conventions.json": "naming_convention",
        "transfer_detection.json": "transfer_detection",
        "deduplication_decisions.json": "deduplication_decision",
        "clarification_outcomes.json": "clarification_outcome",
    }

    for relative_path, memory_type in expected_files.items():
        payload = json.loads((memory_root / relative_path).read_text(encoding="utf-8"))
        assert payload == {
            "schema_version": 1,
            "memory_type": memory_type,
            "records": [],
        }

    index = json.loads(
        (memory_root / "import_sources" / "index.json").read_text(encoding="utf-8")
    )
    assert index == {
        "schema_version": 1,
        "memory_type": "import_source_behavior_index",
        "sources": [],
    }


def test_memory_skill_teaches_exact_file_destinations() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "skill_sources" / "auto-bean-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for required in (
        ".auto-bean/memory/account_mappings.json",
        ".auto-bean/memory/category_mappings.json",
        ".auto-bean/memory/naming_conventions.json",
        ".auto-bean/memory/transfer_detection.json",
        ".auto-bean/memory/deduplication_decisions.json",
        ".auto-bean/memory/clarification_outcomes.json",
        ".auto-bean/memory/import_sources/index.json",
        ".auto-bean/memory/import_sources/<source_slug>.json",
        "read `.auto-bean/memory/import_sources/index.json` first",
    ):
        assert required in text

    assert "memory service" not in text
    assert "Python" not in text


def test_memory_skill_routes_each_category_to_relevant_reference() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "skill_sources" / "auto-bean-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "Read only the reference for the chosen category" in text
    for memory_type, reference in memory_reference_map().items():
        assert f"`{memory_type}`" in text
        assert f".agents/skills/auto-bean-memory/{reference}" in text


def test_memory_reference_examples_match_destinations_and_types() -> None:
    root = Path(__file__).resolve().parents[1]
    references_root = root / "skill_sources" / "auto-bean-memory"
    expected_destinations = {
        "account_mapping": ".auto-bean/memory/account_mappings.json",
        "category_mapping": ".auto-bean/memory/category_mappings.json",
        "naming_convention": ".auto-bean/memory/naming_conventions.json",
        "import_source_behavior": ".auto-bean/memory/import_sources/<source_slug>.json",
        "transfer_detection": ".auto-bean/memory/transfer_detection.json",
        "deduplication_decision": ".auto-bean/memory/deduplication_decisions.json",
        "clarification_outcome": ".auto-bean/memory/clarification_outcomes.json",
    }

    for memory_type, reference in memory_reference_map().items():
        text = (references_root / reference).read_text(encoding="utf-8")
        assert f'"memory_type": "{memory_type}"' in text
        assert expected_destinations[memory_type] in text
        assert '"schema_version": 1' in text

    import_source_text = (
        references_root / memory_reference_map()["import_source_behavior"]
    ).read_text(encoding="utf-8")
    assert ".auto-bean/memory/import_sources/index.json" in import_source_text
    assert '"memory_type": "import_source_behavior_index"' in import_source_text


def memory_reference_map() -> dict[str, str]:
    return {
        "account_mapping": "references/account-mapping.example.md",
        "category_mapping": "references/category-mapping.example.md",
        "naming_convention": "references/naming-convention.example.md",
        "import_source_behavior": "references/import-source-behavior.example.md",
        "transfer_detection": "references/transfer-detection.example.md",
        "deduplication_decision": "references/deduplication-decision.example.md",
        "clarification_outcome": "references/clarification-outcome.example.md",
    }
