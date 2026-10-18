# My Ledger

Operate this workspace in Codex with the Auto Bean plugin enabled.

- Ask `$auto-bean:auto-bean-import` to import statements placed in `statements/raw/`.
- Ask `$auto-bean:auto-bean-query` for balances and activity.
- Ask `$auto-bean:auto-bean-write` to draft or correct transactions.
- Ask Codex to validate the ledger or open Fava using the plugin runtime.

The ledger entrypoint is `ledger.beancount`. Included ledger files live in `beancount/`; evidence and import state live in `statements/`; governed memory and artifacts live in `.auto-bean/`.

The plugin prepares its runtime on demand, including after cloning this workspace onto another supported machine. Install uv and Git, enable the plugin, and open this directory in Codex. Context7 is optional.

Refresh the Auto Bean plugin through Codex to receive product changes. This workspace does not need a standalone auto-bean installation or an update command. Keep runtime caches and migration backups out of Git; retain migration backups locally until you have reviewed preserved customizations.
