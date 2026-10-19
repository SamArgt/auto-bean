# Plugin execution

The installed plugin owns skills, references, helpers, and runtime dependencies. The selected user workspace owns financial files, evidence, governed memory, and artifacts. Never write user data into the plugin or copy its skills into the workspace.

Resolve this file and other relative resources from the loaded skill's actual location, not from the shell working directory. For a skill at `<plugin>/skills/<name>/SKILL.md`, the plugin root is two directories above the skill directory. Resolve the workspace from the current ledger project or the user's explicit target. Ask when multiple workspaces are plausible. Never save the plugin's absolute cache path in workspace files.

For shell examples in these skills, set the following variables to the discovered absolute paths and define this function in the same shell invocation as the command:

```sh
# Set AUTO_BEAN_PLUGIN to the discovered installed plugin root.
# Set AUTO_BEAN_WORKSPACE to the selected ledger directory.
auto_bean() {
    sh "$AUTO_BEAN_PLUGIN/runtime/launch.sh" run --workspace "$AUTO_BEAN_WORKSPACE" "$@"
}
```

Then run commands such as:

```sh
auto_bean bean-check ledger.beancount
auto_bean bean-query ledger.beancount 'SELECT account, sum(position) GROUP BY account;'
auto_bean fava ledger.beancount --host 127.0.0.1
```

The launcher prepares uv-managed Python and the locked base runtime on demand. Only Docling or `ensure-runtime --extraction` prepares the separate extraction generation; queries, validation, and initialization do not download Docling or Torch. Its disposable cache is the only setup write allowed during a read-only query; financial files and governed state remain read-only. It requires uv on macOS or Linux. Initialization also requires Git. No standalone auto-bean installation, global activation, workspace `.venv`, or `auto-bean update` is needed.

Before an operation on an existing workspace, read `.auto-bean/workspace.json`. Initialization is exempt because it creates that marker; migration may read a legacy workspace without it. If absent in a legacy auto-bean ledger, use `$auto-bean:auto-bean-migrate`; do not fall back to stale workspace skills. An unsupported format needs a compatible plugin, not guessed schema repair. Missing required packaged resources or failed runtime preparation block dependent work.

Use Context7 when available for current library documentation. Otherwise use the official Beancount, Beanquery, Docling, Fava, or Beanprice documentation. If authoritative documentation is needed for a decision and cannot be accessed, stop that decision and explain what is missing. Never require an API key just to initialize a ledger. Existing user MCP configuration belongs to the user.

Include the selected workspace and actual packaged skill/reference locations in sub-agent handoffs. Keep one operation on its loaded plugin release; after a plugin refresh, use a fresh chat when necessary to discover the new release. Do not invent cache paths, update plugin files, or install a scheduler.

`auto_bean python` provides the runtime Python for bounded JSON inspection or other evidence processing. Prefer the examples in the parsed-statement reading reference; jq is optional. Read [state validation](state-validation.md) when checking structured workflow state. Poll long-running extraction, price, or Fava sessions according to the task; an initial empty output chunk does not mean completion.
