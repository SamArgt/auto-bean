# Local review UI compatibility probe

This is milestone 1 of the import review UI plan. It is an isolated synthetic
plugin, not the auto-bean product UI. It never opens a ledger, changes import
schemas, or changes Harbor grading. The product implementation must wait until
the desktop checks below pass.

## Run the protocol check

From the repository root:

```sh
UV_CACHE_DIR=/tmp/auto-bean-ui-uv-cache uv run --frozen --project experiments/review-ui-probe python experiments/review-ui-probe/check.py
```

This starts the official Python MCP SDK server over stdio and verifies tool
discovery, HTML resource retrieval, a structured synthetic session, persisted
idempotent actions, and rejection of an invalid action ID. It uses an isolated
temporary directory and cleans its test data on exit. It does not prove that
the desktop renderer or conversation bridge works.

The small HTML view uses the documented MCP Apps JSON-RPC bridge directly for
the compatibility test. The full product UI remains planned in React/TypeScript
with the MCP Apps SDK. The lockfile pins the probe's Python dependencies.

## Installed test package

On 2026-10-21 an isolated copy of the package was installed as
`auto-bean-review-probe@auto-bean-ui-probe`. Its temporary marketplace source is
`.cache/review-ui-probe-marketplace`. It is separate from `auto-bean@auto-bean`.
The package copy contains only the manifest, MCP configuration, lockfile,
Python project, server, and HTML view; it excludes the development virtualenv.

Codex CLI 0.163.0 confirmed through `plugin/read` that the plugin is installed,
enabled, and declares the `review-probe` MCP server. After a tool refresh, the
current conversation exposed `open_review_probe` and opened its panel.

## Required desktop check

1. Select **Auto Bean Review Probe** in the existing conversation's plugin
   picker. Refresh the plugin list if necessary.
2. Open **Import Review Probe** from the conversation's panel controls or call
   its `open_review_probe` tool.
3. Confirm the view displays **Host bridge connected**.
4. Choose **Read synthetic session**. Confirm `example.csv` and `account_review`.
5. Choose **Save test action**. Confirm one synthetic action is persisted.
6. Choose **Continue this conversation**. Verify the message arrives in the
   originating conversation and the agent can resume.
7. Reopen the view and read again to confirm saved actions survive the view.

The continuation message contains only a synthetic action ID and test purpose.
No financial data is read or transmitted. Saving alone never sends a message;
the separate continuation button is an explicit test action.

## Evidence and completion boundary

Verified on 2026-10-21:

- Real stdio discovery, resource read, structured read, persistence,
  idempotency, and invalid-input rejection passed.
- Installed plugin metadata reports enabled state and the local MCP server.
- Existing product and Harbor host tests passed: 89 tests.
- Root Mypy passed: 31 source files; the two standalone probe files also passed
  a separate check using the probe virtualenv as the Python executable.
- The actual desktop host rendered the panel. Its initialization reported
  `hostInfo.name: chatgpt`, version `26.1016.51333`, desktop platform, and
  `serverTools`, `serverResources`, and `message` capabilities.
- The panel's **Read synthetic session** button fetched `example.csv` in
  `account_review` through the host bridge.
- **Save test action** persisted `da987fcc-6568-4978-8dbe-f19facb2f9c6`;
  a subsequent model-side `open_review_probe` call returned that action.
- **Continue this conversation** received a successful host response. The corresponding MCP app message arrived in the same conversation with the
  matching saved action ID; implementation resumed successfully.

Not yet verified:

- State restoration after closing and reopening the panel.

The computer-use tool explicitly refuses to control `com.openai.codex`:
`Computer Use is not allowed to use the app 'com.openai.codex' for safety reasons.`
After tool refresh, the tool call opened the panel and the permitted MCP Apps
browser surface could inspect it and click its controls. Native app control
was not needed. Local rendering and bridge calls are supported on this build.

The full parsed-v2, staged approval, panel, skills, and Harbor changes are not
implemented. Do not describe this probe or the existing 89 passing tests as
acceptance of that feature.

## References

- [OpenAI MCP Extensions](https://github.com/openai/mcp-extensions/blob/main/docs/spec.md)
- [Integration patterns](https://github.com/openai/mcp-extensions/blob/main/docs/patterns.md)
- [MCP Apps](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/draft/apps.mdx)
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)
