# Review UI specification review

Reviewed on 2026-11-06. Scope: the plugin's MCP server, React Review UI,
host bridge, build output, and relevant tests.

## References

- [MCP Apps SDK and API](https://apps.extensions.modelcontextprotocol.io/api/)
- [Stable MCP Apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- [OpenAI MCP Extensions specification](https://github.com/openai/mcp-extensions/blob/main/docs/spec.md)
- [OpenAI integration patterns](https://github.com/openai/mcp-extensions/blob/main/docs/patterns.md)

SDK usage was also checked against the installed MCP Apps version, 1.7.5,
through Context7. The current API guide states that versions 1 and 2 share
the wire protocol. A major SDK upgrade is not required for these fixes.

## Findings and changes

| Area | Finding | Change |
| --- | --- | --- |
| Startup | An early tool result could mount the polling UI before connection completed. | Hold the binding until the host connection is ready. |
| Lifecycle | Failed and cancelled entrypoints had no specific error view. A late connection could render after teardown. | Show a recoverable error and prevent rendering after teardown. |
| Binding | Tool results used an unchecked type assertion. An empty entrypoint could leave an old session selected. | Check binding fields and handle an explicit null binding. Ignore unrelated success results. |
| Capabilities | Unsupported hosts could start repeated tool calls or offer a send action that cannot work. | Check server-tool support before mounting. Disable sending when the message extension is absent. Keep saved review data accessible. |
| Host appearance | Font declarations, safe-area insets, and the host cursor preference were not applied. | Apply initial and changed font/inset values. Use host cursor variables. Keep the fixed footer inside the safe area. |
| Small screens | The sidebar left little room for content at phone widths. | Stack navigation above content below 600 pixels. Bound footer height and allow it to scroll. |
| Polling | Each successful poll recreated the catalog and fetched all account counts again. | Preserve unchanged catalog state. Refresh counts after saves, explicit refreshes, evidence changes, and failed reads. |
| Tool responses | A success envelope without a result could reach a form as undefined data. | Reject incomplete success envelopes at the bridge. |
| Resource metadata | The border preference was implicit. App and server versions lagged behind the package. | Set `prefersBorder: false` and align versions to 0.2.2. |

The count optimization compares the complete statement detail. It does not
cache validation based only on a statement etag. Validation and received-input
state can change independently. Normal polling still reads current evidence.
The regression test confirms that three unchanged polls add no account-count
requests. A failed count request retries on the next poll.

## Existing contracts retained

- Register host handlers before `connect()`.
- Use SDK transport methods instead of custom `postMessage` handlers.
- Accept `{}` for the thread entrypoint.
- Publish HTML as `text/html;profile=mcp-app` under a `ui://` URI.
- Use a bundle hash in the resource URI to invalidate host caches.
- Declare fullscreen support in both app capabilities and resource metadata.
- Restrict review helper tools to app visibility.
- Bundle scripts and styles locally. Declare no external connection or resource domains.
- Send continuation messages only from the explicit **Send saved changes** action.
- Use `openai/files/open` for server-provided export paths when supported.
- Keep review saves separate from canonical ledger writes.
- Preserve stale-edit checks, draft guards, hidden-tab polling suspension,
  structured tool schemas, and error results.

## Verification

| Check | Result |
| --- | --- |
| Frontend build and TypeScript | Passed; packaged HTML and build hashes regenerated |
| Vitest | 52 tests passed, including startup, teardown, capabilities, and polling regressions |
| Python tests | 208 tests passed, including real stdio discovery, resource metadata, saves, stale edits, and packaging |
| Ruff check and format | Passed |
| mypy | Passed for 45 source files |
| Browser layout | Inspected at 375 × 812, 768 × 1024, and 1440 × 900; no page-level horizontal overflow |
| Browser interaction | Account navigation and transaction dialog open/close checked; light and dark appearances inspected |

Browser checks used the shared React UI with synthetic demo data. Host lifecycle
tests use a simulated SDK host. The rebuilt plugin was not reinstalled into
Codex during this review. A live check of the updated panel's continuation and
file-open handoff remains necessary after the plugin is reloaded.
