import { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Review } from "./Review";
import type { Bridge } from "./types";
// The experiment adapter and its fixtures have no runtime plugin dependency.
// @ts-expect-error The demo adapter is tested as a JavaScript module.
import { createDemoBridge } from "../../../experiments/review-ui-design/bridge.mjs";
import "./style.css";

function Demo() {
  const stage =
    new URLSearchParams(location.search).get("stage") ?? "transactions";
  const [state, setState] = useState<unknown>(null);
  const fail = useRef(false);
  const bridge = useMemo(
    () => createDemoBridge(stage, setState, { fail: () => fail.current }),
    [stage],
  );
  const [theme, setTheme] = useState("dark");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  const binding = useMemo(
    () => ({ workspace: "Synthetic review experiment", session_id: "demo" }),
    [],
  );
  return (
    <>
      <details className="demo-settings">
        <summary>Demo settings · shared plugin UI · synthetic data</summary>
        <div className="toolbar">
          <a href="/">Transactions</a>
          <a href="/?stage=accounts">Accounts only</a>
          <a href="/?stage=mixed">Mixed stages</a>
          <label>
            Theme
            <select value={theme} onChange={(e) => setTheme(e.target.value)}>
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              onChange={(e) => {
                fail.current = e.target.checked;
              }}
            />
            Simulate save failure
          </label>
          <button
            onClick={async () => {
              await bridge.reset();
              location.reload();
            }}
          >
            Reset demo
          </button>
        </div>
        <p>
          Saves take 0.9 seconds to make progress visible. No ledger changes or
          agent notifications.
        </p>
        <details>
          <summary>Saved JSON / diffs</summary>
          <pre>{JSON.stringify(state, null, 2)}</pre>
        </details>
      </details>
      <Review bridge={bridge as Bridge} initialBinding={binding} />
    </>
  );
}
createRoot(document.getElementById("root")!).render(<Demo />);
