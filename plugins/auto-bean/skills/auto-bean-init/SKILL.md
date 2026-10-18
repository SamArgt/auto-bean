---
name: auto-bean-init
description: Initialize a new local Beancount ledger with the auto-bean Codex plugin, including its workspace, managed runtime, validation, and initial Git history. Use after plugin installation or when the user asks to create a ledger.
---

Read [plugin execution](../../references/plugin-execution.md). Resolve bundled resources from this installed skill's location.

1. Identify the intended absolute destination. Use the user's selected empty directory when clear; otherwise ask for the destination. Do not initialize the product repository or overwrite a nonempty directory. For an existing auto-bean ledger, use `$auto-bean:auto-bean-migrate`.
2. Explain any missing uv or Git prerequisite with its official installation instructions. Let uv manage Python 3.13 and the ledger dependencies. Do not install machine prerequisites or change global Git identity without the user's request.
3. Run the bundled helper with the resolved plugin and workspace paths:

   ```sh
   sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" init --workspace "$AUTO_BEAN_WORKSPACE"
   ```

4. Inspect the structured result and terminal exit status. `ok` means runtime preparation and ledger validation passed and the initial commit succeeded. `needs_input` means the validated workspace is preserved but Git finalization needs attention; explain the returned step. A failed command is not successful setup.
5. Preserve the template's EUR and account defaults unless the user requested others. Route requested ledger changes through `$auto-bean:auto-bean-write`, validate, and review them in conversation. Do not invent opening balances or personal account identities.
6. Tell the user where the ledger was created and how to operate it: `$auto-bean:auto-bean-import` for statements, `$auto-bean:auto-bean-query` for reads, `$auto-bean:auto-bean-write` for entries, and the runtime launcher for Fava. Ask the user to open the new directory as their Codex project if this chat still targets another directory. Never push automatically.

The plugin remains the execution surface. Do not copy skills, helpers, or maintenance scripts into the new ledger, or configure a Context7 connection during setup.
