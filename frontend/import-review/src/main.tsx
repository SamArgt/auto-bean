import {
  App,
  applyDocumentTheme,
  applyHostStyleVariables,
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
  { name: "Auto Bean Import Review", version: "0.2.0" },
  { availableDisplayModes: ["fullscreen"] },
);
const extensions = new OpenAIExtensions(app);
const bridge = createBridge(app, extensions);
let binding: Binding | null = null;
const render = () =>
  root.render(<Review bridge={bridge} initialBinding={binding} />);
app.ontoolresult = (result) => {
  const data = result.structuredContent as
    { result?: { binding?: Binding } } | undefined;
  if (data?.result?.binding) {
    binding = data.result.binding;
    render();
  }
};
app.onhostcontextchanged = (context) => {
  if (context.theme) applyDocumentTheme(context.theme);
  if (context.styles?.variables)
    applyHostStyleVariables(context.styles.variables);
};
app.onteardown = async () => {
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
    const context = app.getHostContext();
    if (context?.theme) applyDocumentTheme(context.theme);
    if (context?.styles?.variables)
      applyHostStyleVariables(context.styles.variables);
    render();
  })
  .catch((error) =>
    root.render(
      <main>
        <h1>Import review unavailable</h1>
        <p role="alert">{String(error)}</p>
        <p>
          The local host bridge could not connect. Continue review in the
          conversation.
        </p>
      </main>,
    ),
  );
