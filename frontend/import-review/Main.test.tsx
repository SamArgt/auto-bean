// @vitest-environment jsdom
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { App, McpUiHostContext } from "@modelcontextprotocol/ext-apps";

const host = vi.hoisted(() => ({
  app: {
    connect: vi.fn(),
    getHostCapabilities: vi.fn(),
    getHostContext: vi.fn(),
    ontoolresult: undefined as App["ontoolresult"],
    ontoolcancelled: undefined as App["ontoolcancelled"],
    onhostcontextchanged: undefined as App["onhostcontextchanged"],
    onteardown: undefined as App["onteardown"],
  },
  render: vi.fn(),
  unmount: vi.fn(),
  theme: vi.fn(),
  variables: vi.fn(),
  fonts: vi.fn(),
}));
vi.mock("@modelcontextprotocol/ext-apps", () => ({
  App: class {
    constructor() {
      return host.app;
    }
  },
  applyDocumentTheme: host.theme,
  applyHostStyleVariables: host.variables,
  applyHostFonts: host.fonts,
}));
vi.mock("@openai/mcp-extensions/app", () => ({ OpenAIExtensions: class {} }));
vi.mock("react-dom/client", () => ({
  createRoot: () => ({ render: host.render, unmount: host.unmount }),
}));
vi.mock("./src/Review", () => ({
  Review: ({ initialBinding }: { initialBinding: unknown }) => (
    <p>Review: {JSON.stringify(initialBinding)}</p>
  ),
}));

let connect: () => void;
const markup = () => renderToStaticMarkup(host.render.mock.lastCall![0]);
const binding = { workspace: "/ledger", session_id: "session" };
const result = (value: unknown) => ({
  content: [],
  structuredContent: { status: "ok", result: { binding: value } },
});

beforeEach(async () => {
  vi.resetModules();
  vi.clearAllMocks();
  document.body.innerHTML = '<div id="root"></div>';
  document.documentElement.removeAttribute("style");
  host.app.getHostCapabilities.mockReturnValue({ serverTools: {} });
  host.app.getHostContext.mockReturnValue(undefined);
  host.app.connect.mockImplementation(
    () =>
      new Promise<void>((resolve) => {
        connect = resolve;
      }),
  );
  await import("./src/main");
});
afterEach(async () => {
  await host.app.onteardown!({});
});

test("early tool results wait for connection and apply initial and changed host styles", async () => {
  host.app.ontoolresult!(result(binding));
  expect(markup()).toContain("Connecting");
  const context: McpUiHostContext = {
    theme: "dark",
    styles: {
      variables: { "--color-text-primary": "white" },
      css: { fonts: "body { font-family: system-ui; }" },
    },
    safeAreaInsets: { top: 12, right: 4, bottom: 30, left: 4 },
  };
  host.app.getHostContext.mockReturnValue(context);
  connect();
  await vi.waitFor(() => expect(markup()).toContain("/ledger"));
  expect(host.theme).toHaveBeenCalledWith("dark");
  expect(host.variables).toHaveBeenCalledWith(context.styles!.variables);
  expect(host.fonts).toHaveBeenCalledWith(context.styles!.css!.fonts);
  expect(
    document.documentElement.style.getPropertyValue("--safe-area-bottom"),
  ).toBe("30px");
  host.app.onhostcontextchanged!({
    safeAreaInsets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  expect(
    document.documentElement.style.getPropertyValue("--safe-area-bottom"),
  ).toBe("0px");
});
test("failed and cancelled entrypoints display a recoverable error", async () => {
  host.app.ontoolresult!({
    isError: true,
    content: [{ type: "text", text: "Session is missing" }],
  });
  connect();
  await vi.waitFor(() => expect(markup()).toContain("Session is missing"));
  host.app.ontoolresult!(result(binding));
  expect(markup()).toContain("/ledger");
  host.app.ontoolcancelled!({ reason: "cancelled" });
  expect(markup()).toContain("cancelled");
});
test("empty entrypoints clear old bindings and malformed bindings are rejected", async () => {
  connect();
  await vi.waitFor(() => expect(markup()).toContain("Review:"));
  host.app.ontoolresult!(result(binding));
  host.app.ontoolresult!({
    content: [],
    structuredContent: { result: { rows: [] } },
  });
  expect(markup()).toContain("/ledger");
  host.app.ontoolresult!(result(null));
  expect(markup()).toContain("Review: null");
  host.app.ontoolresult!(result({ workspace: 42 }));
  expect(markup()).toContain("invalid review session");
});
test("hosts without server tools do not mount a polling review", async () => {
  host.app.getHostCapabilities.mockReturnValue({});
  connect();
  await vi.waitFor(() =>
    expect(markup()).toContain("cannot access the local review tools"),
  );
  expect(markup()).not.toContain("Review:");
});
test("teardown during connection prevents a late render", async () => {
  await host.app.onteardown!({});
  const renders = host.render.mock.calls.length;
  connect();
  await Promise.resolve();
  host.app.ontoolresult!(result(binding));
  expect(host.render).toHaveBeenCalledTimes(renders);
});
