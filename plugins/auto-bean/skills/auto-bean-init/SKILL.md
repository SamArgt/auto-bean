---
name: auto-bean-init
description: Initialize a new local Beancount ledger with the auto-bean Codex plugin, including its workspace, managed runtime, validation, and initial Git history. Use after plugin installation or when the user asks to create a ledger.
---

Read [common guidance](../../references/common.md#runtime) once for workspace resolution and launcher setup.

1. Select an unambiguous absolute, empty destination; ask if unclear. Exclude the product repository; route existing ledgers to `$auto-bean:auto-bean-migrate`.
2. Report missing uv/Git with official installation guidance; uv manages Python 3.13/dependencies. Prerequisite installation, global Git identity, MCP configuration, and pushing require explicit requests.
3. Keep EUR/account defaults unless requested otherwise; append `--currency <SYMBOL>` for a requested operating currency:

   ```sh
   sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" init --workspace "$AUTO_BEAN_WORKSPACE"
   ```

4. Check JSON result and terminal exit: `ok` means validated and initially committed; `needs_input` preserves a validated workspace needing Git attention. Report its next step; failure is not successful setup.
5. Own other explicitly requested scaffold options/account-name changes under Write's [direct-review procedure](../auto-bean-write/SKILL.md#direct-review); apply them before claiming those preferences are configured. Route transactions to `$auto-bean:auto-bean-write`. Never invent opening balances, personal accounts, or preferences.
6. Return the destination and routes for statements (`$auto-bean:auto-bean-import`), reads (`$auto-bean:auto-bean-query`), transactions, and launcher-based Fava. Have the user open the new project if this chat targets another directory. Installed plugin resources stay in the plugin.
