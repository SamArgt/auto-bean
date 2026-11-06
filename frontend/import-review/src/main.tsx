import {
  App,
  applyDocumentTheme,
  applyHostStyleVariables,
  applyHostFonts,
  type McpUiHostContext,
} from "@modelcontextprotocol/ext-apps";
import { OpenAIExtensions } from "@openai/mcp-extensions/app";
import { createRoot } from "react-dom/client";
import { Review } from "./Review";
import type { Binding } from "./types";
import { createBridge } from "./bridge";
import "@openai/mcp-extensions/app/styles.css";
import "./style.css";
const root = createRoot(document.getElementById("root")!);
const app = new App(
  { name: "Auto Bean Import Review", version: "0.2.2" },
  { availableDisplayModes: ["fullscreen"] },
);
const extensions = new OpenAIExtensions(app);
const bridge = createBridge(app, extensions);
let binding: Binding | null = null;
let connected = false;
let disposed = false;
let startupError = "";
const render = () => {
  if (disposed) return;
  if (startupError) {
    root.render(
      <main>
        <h1>Import review unavailable</h1>
        <p role="alert">{startupError}</p>
        <p>
          Reopen the panel to retry, or continue review in the conversation.
        </p>
      </main>,
    );
  } else if (connected) {
    root.render(<Review bridge={bridge} initialBinding={binding} />);
  }
};
app.ontoolresult = (result) => {
  if (disposed) return;
  if (result.isError) {
    startupError =
      result.content
        .filter((item) => item.type === "text")
        .map((item) => item.text)
        .join("\n") || "The review session could not be opened.";
  } else {
    const value = result.structuredContent?.result;
    // Only the entrypoint result can bind or clear this panel.
    if (!value || typeof value !== "object" || !("binding" in value)) return;
    const candidate = value.binding;
    if (candidate === null) {
      binding = null;
      startupError = "";
    } else if (
      typeof candidate === "object" &&
      "workspace" in candidate &&
      typeof candidate.workspace === "string" &&
      candidate.workspace.trim() &&
      "session_id" in candidate &&
      typeof candidate.session_id === "string" &&
      candidate.session_id.trim()
    ) {
      binding = {
        workspace: candidate.workspace,
        session_id: candidate.session_id,
      };
      startupError = "";
    } else {
      startupError = "The host returned an invalid review session.";
    }
  }
  render();
};
app.ontoolcancelled = () => {
  startupError = "Opening the review session was cancelled.";
  render();
};
function applyHostContext(context: McpUiHostContext) {
  if (context.theme) applyDocumentTheme(context.theme);
  if (context.styles?.variables)
    applyHostStyleVariables(context.styles.variables);
  if (context.styles?.css?.fonts) applyHostFonts(context.styles.css.fonts);
  if (context.safeAreaInsets) {
    for (const [edge, pixels] of Object.entries(context.safeAreaInsets)) {
      document.documentElement.style.setProperty(
        `--safe-area-${edge}`,
        `${pixels}px`,
      );
    }
  }
}
app.onhostcontextchanged = applyHostContext;
app.onteardown = async () => {
  disposed = true;
  root.unmount();
  return {};
};
root.render(
  <main>
    <h1>Import review</h1>
    <p role="status">Connecting to the local review service…</p>
  </main>,
);
app
  .connect()
  .then(() => {
    if (disposed) return;
    if (!app.getHostCapabilities()?.serverTools)
      throw new Error(
        "This host cannot access the local review tools. Update the host or continue in the conversation.",
      );
    connected = true;
    const context = app.getHostContext();
    if (context) applyHostContext(context);
    render();
  })
  .catch((error) => {
    startupError = String(error);
    render();
  });
