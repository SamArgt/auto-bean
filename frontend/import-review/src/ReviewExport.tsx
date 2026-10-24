import { useState } from "react";
import type { Binding, Bridge } from "./types";

type ExportResult = {
  path: string;
  filename: string;
  sha256: string;
  exported_at: string;
};

export function ReviewExport({
  bridge,
  binding,
}: {
  bridge: Bridge;
  binding: Binding;
}) {
  const [result, setResult] = useState<ExportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      setResult(
        await bridge.call<ExportResult>("export_import_review", binding),
      );
    } catch (e) {
      setError(`HTML export failed: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  }
  async function open() {
    if (!result || !bridge.openFile) return;
    setError("");
    try {
      await bridge.openFile(result.path);
    } catch (e) {
      setError(`The HTML file is saved, but could not be opened: ${String(e)}`);
    }
  }
  return (
    <section aria-label="HTML export">
      <button onClick={() => void save()} disabled={busy}>
        {busy ? "Saving HTML…" : "Export HTML"}
      </button>
      <span className="muted">
        {" "}
        Read-only snapshot of this session’s saved review. Unsaved edits are
        excluded.
      </span>
      {error && <p role="alert">{error}</p>}
      {result && (
        <div role="status">
          <p>
            Saved {result.filename} · {result.exported_at}
          </p>
          <p className="context">{result.path}</p>
          <p className="muted">
            Open this self-contained file in a browser, or copy it to keep or
            share the review. It includes this import’s financial data.
          </p>
          {bridge.openFile && (
            <button onClick={() => void open()}>Open saved HTML</button>
          )}
        </div>
      )}
    </section>
  );
}
