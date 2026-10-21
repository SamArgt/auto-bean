import { expect, test, vi } from "vitest";
import type { App } from "@modelcontextprotocol/ext-apps";
import type { OpenAIExtensions } from "@openai/mcp-extensions/app";
import { createBridge } from "./src/bridge";
test("local file capability is checked after the host connects", async () => {
  let files: { open: ReturnType<typeof vi.fn> } | undefined;
  const bridge = createBridge(
    { callServerTool: vi.fn() } as unknown as App,
    {
      message: undefined,
      get files() {
        return files;
      },
    } as unknown as OpenAIExtensions,
  );
  await expect(bridge.openFile!("/ledger/export.html")).rejects.toThrow(
    "saved path",
  );
  files = { open: vi.fn().mockResolvedValue({}) };
  await bridge.openFile!("/ledger/export.html");
  expect(files.open).toHaveBeenCalledExactlyOnceWith("/ledger/export.html");
});
test("protocol validation errors expose their diagnostic text", async () => {
  const bridge = createBridge(
    {
      callServerTool: vi.fn().mockResolvedValue({
        isError: true,
        content: [{ type: "text", text: "account_id must be a stable ID" }],
      }),
    } as unknown as App,
    { message: undefined } as unknown as OpenAIExtensions,
  );
  await expect(bridge.call("list_import_transactions", {})).rejects.toThrow(
    "account_id must be a stable ID",
  );
});
test("a host rejection is a failed continuation, not a successful notification", async () => {
  const send = vi.fn().mockResolvedValue({ isError: true });
  const bridge = createBridge(
    { callServerTool: vi.fn() } as unknown as App,
    { message: { send } } as unknown as OpenAIExtensions,
  );
  await expect(
    bridge.continue("session", "statements/raw/a.csv"),
  ).rejects.toThrow("decision remains saved");
  expect(send).toHaveBeenCalledWith({
    role: "user",
    content: [
      {
        type: "text",
        text: expect.stringContaining(
          "session session: review of statements/raw/a.csv was updated",
        ),
      },
    ],
    _meta: { "openai/message": { target: "active", send: true } },
  });
});
test("structured tool errors remain visible to the calling form", async () => {
  const bridge = createBridge(
    {
      callServerTool: vi.fn().mockResolvedValue({
        structuredContent: {
          status: "error",
          error_code: "edit_conflict",
          message: "Refresh before retry",
        },
      }),
    } as unknown as App,
    { message: undefined } as unknown as OpenAIExtensions,
  );
  await expect(bridge.call("update_import_review", {})).rejects.toThrow(
    "edit_conflict",
  );
});
