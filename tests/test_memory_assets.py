from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from auto_bean.init import (
    CommandResult,
    InitContext,
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
    assert (
        root / "skill_sources" / "shared" / "parsed-statement-output.example.json"
    ).is_file()
    assert (
        root / "skill_sources" / "shared" / "parsed-statement-jq-reading.md"
    ).is_file()
    assert (
        root / "workspace_template" / ".auto-bean" / "artifacts" / "categorize"
    ).is_dir()
    for reference in memory_reference_map().values():
        assert (root / "skill_sources" / "auto-bean-memory" / reference).is_file()


def test_init_required_assets_check_only_skill_entrypoints() -> None:
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
            "auto-bean-categorize/SKILL.md",
            "auto-bean-query/SKILL.md",
            "auto-bean-write/SKILL.md",
            "auto-bean-import/SKILL.md",
            "auto-bean-process/SKILL.md",
            "auto-bean-memory/SKILL.md",
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


def test_update_check_reports_managed_file_diffs_without_overwriting(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    service = InitService(
        paths=ProjectPaths(start=root),
        platform=PlatformProbe(),
        tools=ToolProbe(),
        commands=NoopCommands(),
    )
    target = tmp_path / "workspace"
    service._scaffold_workspace(
        context=make_test_context("workspace", target, root),
        target_directory=target,
    )
    agents = target / "AGENTS.md"
    ledger = target / "ledger.beancount"
    memory = target / ".auto-bean" / "memory" / "account_mappings.json"
    agents.write_text("old agents\n", encoding="utf-8")
    ledger.write_text("ledger stays put\n", encoding="utf-8")
    memory.write_text('{"kept": true}\n', encoding="utf-8")

    result = service.update(str(target), check_only=True)

    assert result.status == "updates_available"
    changed_paths = cast(list[str], result.details["changed_paths"])
    assert "AGENTS.md" in changed_paths
    assert agents.read_text(encoding="utf-8") == "old agents\n"
    assert ledger.read_text(encoding="utf-8") == "ledger stays put\n"
    assert memory.read_text(encoding="utf-8") == '{"kept": true}\n'


def test_update_refreshes_managed_files_without_touching_ledger_or_memory(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    service = InitService(
        paths=ProjectPaths(start=root),
        platform=PlatformProbe(),
        tools=ToolProbe(),
        commands=NoopCommands(),
    )
    target = tmp_path / "workspace"
    service._scaffold_workspace(
        context=make_test_context("workspace", target, root),
        target_directory=target,
    )
    agents = target / "AGENTS.md"
    skill = target / ".agents" / "skills" / "auto-bean-query" / "SKILL.md"
    ledger = target / "ledger.beancount"
    memory = target / ".auto-bean" / "memory" / "account_mappings.json"
    agents.write_text("old agents\n", encoding="utf-8")
    skill.write_text("old skill\n", encoding="utf-8")
    ledger.write_text("ledger stays put\n", encoding="utf-8")
    memory.write_text('{"kept": true}\n', encoding="utf-8")

    result = service.update(str(target))

    assert result.status == "ok"
    updated_paths = cast(list[str], result.details["updated_paths"])
    assert sorted(updated_paths) == [
        ".agents/skills/auto-bean-query/SKILL.md",
        "AGENTS.md",
    ]
    assert agents.read_text(encoding="utf-8") == (
        root / "workspace_template" / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert skill.read_text(encoding="utf-8") == (
        root / "skill_sources" / "auto-bean-query" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert ledger.read_text(encoding="utf-8") == "ledger stays put\n"
    assert memory.read_text(encoding="utf-8") == '{"kept": true}\n'


def test_non_memory_skills_do_not_claim_direct_memory_write_authority() -> None:
    root = Path(__file__).resolve().parents[1]
    direct_write_phrases = (
        "write memory",
        "write repeated-import source context",
        "write only under `.auto-bean/memory",
    )

    for skill_name in (
        "auto-bean-import",
        "auto-bean-process",
        "auto-bean-categorize",
        "auto-bean-query",
        "auto-bean-write",
    ):
        text = (root / "skill_sources" / skill_name / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "auto-bean-memory" in text
        for phrase in direct_write_phrases:
            assert phrase not in text


def test_import_stages_return_memory_suggestions_for_governed_handoff() -> None:
    root = Path(__file__).resolve().parents[1]

    process_text = (
        root / "skill_sources" / "auto-bean-process" / "SKILL.md"
    ).read_text(encoding="utf-8")
    categorize_text = (
        root / "skill_sources" / "auto-bean-categorize" / "SKILL.md"
    ).read_text(encoding="utf-8")
    import_text = (root / "skill_sources" / "auto-bean-import" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for text in (process_text, categorize_text):
        assert "`memory_suggestions`" in text
        assert "`memory_suggestion_files`" in text
        assert ".auto-bean/tmp/memory-suggestions/" in text
        assert "memory type, source context, decision, scope" in text

    assert "Collect and govern memory suggestions" in import_text
    assert "collect `memory_suggestions`" in import_text
    assert "read any returned `memory_suggestion_files`" in import_text
    assert "look for memory suggestion files created during this import" in import_text
    assert "invoke `$auto-bean-memory`" in import_text
    assert (
        "memory suggestions collected and `$auto-bean-memory` persistence result"
        in import_text
    )


def test_categorize_does_not_write_ledger_transactions() -> None:
    root = Path(__file__).resolve().parents[1]
    categorize_text = (
        root / "skill_sources" / "auto-bean-categorize" / "SKILL.md"
    ).read_text(encoding="utf-8")
    import_text = (root / "skill_sources" / "auto-bean-import" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "Do not invoke `$auto-bean-write`." in categorize_text
    assert "Do not write or edit Beancount ledger entries." in categorize_text
    assert "Do not set statements `in_review`" in categorize_text
    assert "invoke `$auto-bean-write`" in import_text
    assert "set `in_review` only after" in import_text


def test_first_seen_account_derivation_belongs_to_import() -> None:
    root = Path(__file__).resolve().parents[1]
    process_text = (
        root / "skill_sources" / "auto-bean-process" / "SKILL.md"
    ).read_text(encoding="utf-8")
    import_text = (root / "skill_sources" / "auto-bean-import" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    process_prompt = (
        root / "skill_sources" / "auto-bean-process" / "agents" / "openai.yaml"
    ).read_text(encoding="utf-8")

    assert "4. Derive first-seen accounts:" in import_text
    assert "process question artifacts under `.auto-bean/artifacts/process/`" in (
        import_text
    )
    assert "update the relevant intermediate parsed statement" in import_text
    assert "do not discover import work, derive first-seen accounts" in process_text
    assert "Do not derive first-seen accounts" in process_text
    assert "Derive first-seen account structure" not in process_text
    assert "make only directly supported first-seen account-structure edits" not in (
        process_prompt
    )


def test_process_and_categorize_share_parsed_statement_references() -> None:
    root = Path(__file__).resolve().parents[1]
    process_text = (
        root / "skill_sources" / "auto-bean-process" / "SKILL.md"
    ).read_text(encoding="utf-8")
    categorize_text = (
        root / "skill_sources" / "auto-bean-categorize" / "SKILL.md"
    ).read_text(encoding="utf-8")
    shared_references = (
        ".agents/skills/shared/parsed-statement-output.example.json",
        ".agents/skills/shared/parsed-statement-jq-reading.md",
    )

    for reference in shared_references:
        assert reference in process_text
        assert reference in categorize_text

    assert (
        ".agents/skills/auto-bean-process/references/parsed-statement-output.example.json"
        not in process_text
    )


class NoopCommands:
    def run(self, args: object, cwd: Path | None = None) -> CommandResult:
        return CommandResult(returncode=0)


def make_test_context(project_name: str, target: Path, root: Path) -> InitContext:
    return InitContext(
        project_name=project_name,
        target_input_type="path",
        working_directory=str(root),
        target_directory=str(target),
        template_directory=str(root / "workspace_template"),
        skill_sources_directory=str(root / "skill_sources"),
    )


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


def test_memory_skill_defines_separate_correction_workflow() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "skill_sources" / "auto-bean-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "## Explicit correction, refinement, and removal workflow" in text
    assert (
        "Keep this path separate from read-only inspection and governed persistence"
        in text
    )
    assert (
        "read `.agents/skills/shared/memory-access-rules.md` before touching runtime memory"
        in text
    )
    assert "memory path plus" in text
    assert "stable record summary" in text
    assert "previous inspection output" in text


def test_memory_skill_correction_covers_fixed_categories_and_import_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "skill_sources" / "auto-bean-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    correction_section = text.split(
        "## Explicit correction, refinement, and removal workflow", maxsplit=1
    )[1]
    for relative_path in (
        "account_mappings.json",
        "category_mappings.json",
        "naming_conventions.json",
        "transfer_detection.json",
        "deduplication_decisions.json",
        "clarification_outcomes.json",
        "import_sources/<source_slug>.json",
    ):
        assert relative_path in correction_section

    assert (
        "read and validate `.auto-bean/memory/import_sources/index.json` first" in text
    )
    assert "only edit source files referenced by valid index entries" in text
    assert (
        "If an import-source file loses all records, keep the empty source file" in text
    )
    assert "keep its index entry" in text


def test_memory_skill_correction_fails_closed_before_rewrite() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "skill_sources" / "auto-bean-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for required in (
        "missing files",
        "invalid JSON",
        "wrong `schema_version`",
        "wrong `memory_type`",
        "missing top-level `records` or `sources`",
        "missing required record fields",
        "path escapes",
        "duplicate target matches",
        "exactly one record",
        "two-space indentation and a trailing newline",
    ):
        assert required in text

    for field in (
        "`schema_version`",
        "`memory_type`",
        "`source`",
        "`decision`",
        "`scope`",
        "`confidence` or `review_state`",
        "`created_at`",
        "`updated_at`",
        "`audit`",
    ):
        assert field in text


def test_memory_skill_correction_output_is_reviewable_without_raw_data() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "skill_sources" / "auto-bean-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for required in (
        "before/after",
        "memory path",
        "target record summary",
        "source context",
        "audit context",
        "future reuse limits",
        "controlled memory change",
        "Story 4.3 inspection path",
        "raw financial statements",
        "full ledger excerpts",
        "unrelated records",
    ):
        assert required in text


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
