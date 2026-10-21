---
name: auto-bean-migrate
description: Switch an existing auto-bean ledger from copied workspace skills and maintenance scripts to the installed Codex plugin. Use for one-time workspace migration or to resume an interrupted migration while preserving financial data and customizations.
---

Read [common guidance](../../references/common.md) once for workspace resolution and execution boundaries.

1. Identify the absolute ledger workspace. Inspect Git status without changing it. Existing uncommitted ledger work belongs to the user; never reset, stash, commit, or push it automatically.
2. Check `.auto-bean/migrations/` for an unfinished journal. If one exists, inspect its changes, backup pointers, and completed operations and use its reviewed plan id to resume. Do not create a competing migration.
3. For a fresh migration, run:

   ```sh
   sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" migrate --workspace "$AUTO_BEAN_WORKSPACE"
   ```

4. Present the concrete removals and documentation diffs directly in conversation. Distinguish manifest-owned retired paths (including customized contents) from unknown files. Unknown files in retired/shared folders are preserved in place; do not infer product ownership from a directory name. Explain that all retired files are backed up outside skill discovery and custom instructions are not merged automatically. Review preserved customizations with the user and port eligible workspace preferences into the stable workspace instructions only when requested. Do not reactivate stale auto-bean skills.
5. Obtain explicit approval of this plan before applying. Then run:

   ```sh
   sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" migrate --workspace "$AUTO_BEAN_WORKSPACE" --apply "$REVIEWED_PLAN_ID"
   ```

6. Inspect the final result and exit status. A stale plan requires a fresh inventory and review; a conflict requires resolving the named path against its backup before resuming the same journal. Never force, remove the journal, or discard user changes to get past a conflict.
7. Confirm validation passed, point to the backup, summarize the diff, and report any custom behavior still needing a decision. Ledger files, statements, parsed evidence, import state, governed memory, Codex configuration, and unrelated skills/scripts must be preserved. Nothing is committed or pushed without user authorization.

After migration, users refresh the plugin through Codex. Do not run the old updater or uninstall global tools automatically. Keep the old `.venv` intact; plugin operations use the fingerprinted runtime cache.

## Import status structure

Check the [status schema](../../references/schemas/status.schema.json) and current state before deciding whether migration is needed; adding optional fields for newly discovered statements does not require converting existing entries. Preserve all existing statement entries, completed imports and their artifacts byte-for-byte. If a future status schema requires migration, inventory and review that narrow change through this migration skill and its journal; do not reconstruct or migrate historical import artifacts.
