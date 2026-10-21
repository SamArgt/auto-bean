import { useCallback, useEffect, useRef, useState } from "react";
import { DraftContext, TextEdit, TransactionCard } from "./ReviewForms";
import { StatementValidation, SessionPrices } from "./ReviewPanels";
import { ReviewExport } from "./ReviewExport";
export { TextEdit } from "./ReviewForms";
import type {
  ReviewUpdate,
  SavedReview,
  SavedPrice,
  Binding,
  Bridge,
  Detail,
  Overview,
  Page,
  Transaction,
} from "./types";

const readable = (s: string) => s.replaceAll("_", " ");
const filename = (s: string) => s.split("/").at(-1) ?? s;
function groupTransactions(rows: Transaction[]): [string, Transaction[]][] {
  const groups = new Map<string, Transaction[]>();
  for (const row of rows.slice(0, 100)) {
    const group = groups.get(row.account_id) ?? [];
    group.push(row);
    groups.set(row.account_id, group);
  }
  return [...groups];
}
export function Review({
  bridge,
  initialBinding,
}: {
  bridge: Bridge;
  initialBinding: Binding | null;
}) {
  return (
    <ReviewSession
      key={
        initialBinding
          ? `${initialBinding.workspace}:${initialBinding.session_id}`
          : "unbound"
      }
      bridge={bridge}
      initialBinding={initialBinding}
    />
  );
}
function ReviewSession({
  bridge,
  initialBinding,
}: {
  bridge: Bridge;
  initialBinding: Binding | null;
}) {
  const [binding, setBinding] = useState(initialBinding),
    [overview, setOverview] = useState<Overview | null>(null);
  const [workspace, setWorkspace] = useState(initialBinding?.workspace ?? ""),
    [sessionId, setSessionId] = useState(initialBinding?.session_id ?? "");
  const [source, setSource] = useState<string | null>(null),
    [detail, setDetail] = useState<Detail | null>(null),
    [page, setPage] = useState<Page | null>(null);
  const [offset, setOffset] = useState(0),
    [account, setAccount] = useState(""),
    [needs, setNeeds] = useState(false),
    [error, setError] = useState(""),
    [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState<Set<string>>(() => new Set());
  const reportDraft = useCallback((id: string, dirty: boolean) => {
    setDrafts((previous) => {
      if (previous.has(id) === dirty) return previous;
      const next = new Set(previous);
      if (dirty) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);
  const [saved, setSaved] = useState<SavedReview | SavedPrice | null>(null),
    [notice, setNotice] = useState(""),
    [accounts, setAccounts] = useState<string[]>([]);
  const [invalidReads, setInvalidReads] = useState({
    summary: false,
    detail: false,
    page: false,
  });
  const request = useRef(0);
  const activeRequest = useRef<string | null>(null);
  const activeSubmission = useRef(false);
  const searchRequest = useRef(0);
  const queryKey = JSON.stringify([binding, source, offset, account, needs]);
  const latestQuery = useRef(queryKey);
  latestQuery.current = queryKey;
  const refresh = useCallback(async () => {
    if (!binding || activeRequest.current === queryKey) return;
    const id = ++request.current;
    activeRequest.current = queryKey;
    const current = () =>
      id === request.current && latestQuery.current === queryKey;
    try {
      const summaryPromise = bridge.call<Overview>(
        "read_import_session",
        binding,
      );
      const detailPromise = source
        ? bridge.call<Detail>("read_import_statement", {
            ...binding,
            source_file: source,
          })
        : Promise.resolve(null);
      const pagePromise = source
        ? bridge.call<Page>("list_import_transactions", {
            ...binding,
            source_file: source,
            offset,
            limit: 100,
            ...(account ? { account_id: account } : {}),
            needs_input: needs,
          })
        : Promise.resolve(null);
      const [summary, d, p] = await Promise.allSettled([
        summaryPromise,
        detailPromise,
        pagePromise,
      ]);
      if (!current()) return;
      if (summary.status === "fulfilled") setOverview(summary.value);
      if (d.status === "fulfilled") setDetail(d.value);
      if (p.status === "fulfilled") setPage(p.value);
      setInvalidReads({
        summary: summary.status === "rejected",
        detail: d.status === "rejected",
        page: p.status === "rejected",
      });
      const failures = [summary, d, p].filter(
        (r): r is PromiseRejectedResult => r.status === "rejected",
      );
      setLoadError(failures.map((f) => String(f.reason)).join(" · "));
    } finally {
      if (id === request.current) activeRequest.current = null;
    }
  }, [bridge, binding, source, offset, account, needs, queryKey]);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => {
      if (!document.hidden) void refresh();
    }, 2000);
    const onVisible = () => {
      if (!document.hidden) void refresh();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      request.current++;
      activeRequest.current = null;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refresh]);
  async function resume(savedReview: SavedReview | SavedPrice) {
    if (!binding) return;
    setError("");
    try {
      await bridge.continue(
        binding.session_id,
        "run_id" in savedReview
          ? `price run ${savedReview.run_id}`
          : savedReview.source_file,
      );
      setNotice(
        "Decision saved. Import agent notified; ledger writing and validation happen in the conversation.",
      );
      setSaved(null);
    } catch (e) {
      setSaved(savedReview);
      setNotice(
        "Decision saved, but the conversation could not resume. Retry sends the notification without saving again.",
      );
      setError(String(e));
    }
  }
  async function submit(update: ReviewUpdate) {
    if (!binding || !source || activeSubmission.current) return false;
    activeSubmission.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await bridge.call<SavedReview>("update_import_review", {
        ...binding,
        source_file: source,
        update,
      });
      setSaved(result);
      setNotice("Decision saved.");
      await resume(result);
      await refresh();
      return true;
    } catch (e) {
      setError(String(e));
      return false;
    } finally {
      activeSubmission.current = false;
      setBusy(false);
    }
  }
  async function approvePrices(runId: string, digest: string) {
    if (!binding || !overview || activeSubmission.current) return;
    activeSubmission.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await bridge.call<SavedPrice>("approve_import_prices", {
        ...binding,
        run_id: runId,
        expected_etag: overview.etag,
        review_digest: digest,
      });
      setSaved(result);
      await resume(result);
      await refresh();
    } catch (error) {
      setError(String(error));
    } finally {
      activeSubmission.current = false;
      setBusy(false);
    }
  }
  async function search(query: string) {
    if (!binding) return;
    const id = ++searchRequest.current,
      key = queryKey;
    try {
      const result = await bridge.call<{ accounts: string[] }>(
        "search_ledger_accounts",
        { ...binding, query },
      );
      if (id === searchRequest.current && latestQuery.current === key)
        setAccounts(result.accounts);
    } catch (e) {
      if (id === searchRequest.current && latestQuery.current === key)
        setError(String(e));
    }
  }
  const selected = overview?.statements.find((s) => s.source_file === source);
  const done = selected?.status === "done";
  const unavailable = Boolean(
    invalidReads.summary || invalidReads.detail || selected?.error,
  );
  const transactionsUnavailable = Boolean(
    invalidReads.summary || invalidReads.page || selected?.error,
  );
  return (
    <DraftContext.Provider value={reportDraft}>
      <main>
        <header>
          <div>
            <span className="eyebrow">AUTO BEAN</span>
            <h1>Import review</h1>
          </div>
          <button onClick={() => void refresh()} disabled={!binding}>
            Refresh
          </button>
        </header>
        {binding && (
          <ReviewExport
            key={`${binding.workspace}:${binding.session_id}`}
            bridge={bridge}
            binding={binding}
          />
        )}
        {!binding ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setBinding({ workspace, session_id: sessionId });
            }}
          >
            <p>Open the session created by your import agent.</p>
            <label>
              Ledger workspace
              <input
                required
                value={workspace}
                onChange={(e) => setWorkspace(e.target.value)}
              />
            </label>
            <label>
              Session ID
              <input
                required
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
              />
            </label>
            <button type="submit">Open session</button>
          </form>
        ) : (
          <div className="context" title={binding.workspace}>
            {binding.workspace}
            <br />
            Session {binding.session_id}
            {!initialBinding && (
              <button
                onClick={() => {
                  setBinding(null);
                  setOverview(null);
                  setSource(null);
                  setDetail(null);
                  setPage(null);
                  setError("");
                  setLoadError("");
                }}
              >
                Change session
              </button>
            )}
          </div>
        )}
        {loadError && (
          <div role="alert" className="error">
            Refresh failed: {loadError}
            <p>
              Displayed results may be stale. Related actions are paused until a
              successful refresh.
            </p>
          </div>
        )}
        {error && (
          <div role="alert" className="error">
            {error}
            <p>
              Your unsaved edits remain in this view. Refresh and review
              conflicts before resubmitting.
            </p>
          </div>
        )}
        {notice && (
          <div role="status" className="notice">
            {notice}
            {saved && (
              <button onClick={() => void resume(saved)}>
                Retry continuation
              </button>
            )}
          </div>
        )}
        {overview && (
          <>
            <nav aria-label="Session statements">
              <button
                aria-pressed={!source}
                onClick={() => {
                  setSource(null);
                  setDetail(null);
                  setPage(null);
                }}
              >
                Session & prices
              </button>
              {overview.statements.map((s) => (
                <button
                  className={s.needs_input ? "needs" : ""}
                  aria-pressed={source === s.source_file}
                  key={s.source_file}
                  onClick={() => {
                    if (source === s.source_file) return;
                    setSource(s.source_file);
                    setDetail(null);
                    setPage(null);
                    setOffset(0);
                    setAccount("");
                  }}
                >
                  <strong>{filename(s.source_file)}</strong>
                  <span>
                    Group: {readable(s.status)}
                    {s.needs_input > 0
                      ? ` · ⚠ ${s.needs_input} need input`
                      : ""}
                  </span>
                  {s.error && <span>Artifact unavailable</span>}
                </button>
              ))}
            </nav>
            {source ? (
              <>
                <h2>{filename(source)}</h2>
                <p className="context">
                  Group status: {readable(selected?.status ?? "unavailable")} ·{" "}
                  {selected?.updated_at
                    ? `Updated ${selected.updated_at}`
                    : "Update time unavailable"}
                </p>
                {selected?.error && (
                  <div className="error" role="alert">
                    {selected.error}
                  </div>
                )}
                {done && (
                  <p className="notice">
                    This statement is complete. Request explicit rework in the
                    conversation before changing its decisions.
                  </p>
                )}
                {detail && (
                  <>
                    <p>Extraction: {readable(detail.extraction_state)}</p>
                    {detail.processing.failure_reason && (
                      <p className="error">
                        {detail.processing.failure_reason}
                      </p>
                    )}
                    {detail.processing.warnings.map((w, i) => (
                      <p className="notice" key={i}>
                        {w}
                      </p>
                    ))}
                    {detail.processing.needs_input && (
                      <section className="card needs">
                        <h3>⚠ Processing needs input</h3>
                        {detail.processing.suggestions?.length ? (
                          <ul>
                            {detail.processing.suggestions.map((suggestion) => (
                              <li key={suggestion}>{suggestion}</li>
                            ))}
                          </ul>
                        ) : null}
                        <TextEdit
                          label="Processing answer"
                          value={detail.processing.answer ?? ""}
                          etag={detail.etag}
                          disabled={busy || unavailable || done}
                          saveLabel="Save answer"
                          onSave={(value, etag) =>
                            submit({
                              kind: "answer",
                              subject_kind: "statement",
                              subject_id: "statement",
                              value,
                              expected_etag: etag,
                            })
                          }
                        />
                      </section>
                    )}
                    {!detail.processing.needs_input &&
                      detail.processing.answer && (
                        <p>
                          Saved processing answer: {detail.processing.answer}
                        </p>
                      )}
                    <h3>Accounts & balances</h3>
                    {detail.statement_metadata.accounts.length === 0 ? (
                      <p className="muted">
                        Account evidence is not available yet.
                      </p>
                    ) : (
                      detail.statement_metadata.accounts.map((a) => {
                        const d = a.review;
                        return (
                          <section
                            className={`card ${d?.state === "needs_input" ? "needs" : ""}`}
                            key={a.account_id}
                          >
                            <h4>
                              {d?.state === "needs_input"
                                ? "⚠ Needs input · "
                                : ""}
                              {a.account_name ?? a.account_id}
                            </h4>
                            {a.account_owner && <p>{a.account_owner}</p>}
                            <p>
                              {d?.rationale ??
                                "Mapping proposal not available yet."}
                            </p>
                            {d?.suggestions?.length ? (
                              <ul>
                                {d.suggestions.map((suggestion) => (
                                  <li key={suggestion}>{suggestion}</li>
                                ))}
                              </ul>
                            ) : null}
                            {d?.answer && <p>Saved answer: {d.answer}</p>}
                            {d && (
                              <TextEdit
                                label="Ledger mapping"
                                value={d.ledger_account ?? ""}
                                etag={detail.etag}
                                suggestions={accounts}
                                onSearch={search}
                                disabled={busy || unavailable || done}
                                allowConfirm={d.state === "needs_input"}
                                onSave={(value, etag) =>
                                  submit({
                                    kind: "mapping",
                                    subject_id: a.account_id,
                                    value,
                                    expected_etag: etag,
                                  })
                                }
                              />
                            )}
                            {d?.state === "needs_input" && (
                              <details>
                                <summary>Other account clarification</summary>
                                <TextEdit
                                  label="Account answer"
                                  value={d.answer ?? ""}
                                  etag={detail.etag}
                                  disabled={busy || unavailable || done}
                                  saveLabel="Save answer"
                                  onSave={(value, etag) =>
                                    submit({
                                      kind: "answer",
                                      subject_kind: "account",
                                      subject_id: a.account_id,
                                      value,
                                      expected_etag: etag,
                                    })
                                  }
                                />
                              </details>
                            )}
                            <dl>
                              {(
                                [
                                  "opening_balance",
                                  "closing_balance",
                                  "available_balance",
                                ] as const
                              ).map((key) => (
                                <div key={key}>
                                  <dt>{readable(key)}</dt>
                                  <dd>
                                    {a[key]
                                      ? `${a[key].amount} ${a[key].currency} · ${a[key].date}`
                                      : "Unavailable"}
                                  </dd>
                                </div>
                              ))}
                            </dl>
                            {d?.proposed_directives?.map((line, i) => (
                              <pre key={i}>{line}</pre>
                            ))}
                            {d?.reconciliation?.map((r, i) => (
                              <p key={i}>
                                Ledger {r.ledger_amount ?? "unavailable"}{" "}
                                {r.currency} on {r.date} · {readable(r.state)}
                                {r.difference !== undefined
                                  ? ` · Difference ${r.difference}`
                                  : ""}
                                <br />
                                <small>{r.provenance}</small>
                              </p>
                            ))}
                          </section>
                        );
                      })
                    )}
                    <h3>Transactions</h3>
                    <div className="filters">
                      <label>
                        Account
                        <select
                          value={account}
                          onChange={(e) => {
                            setAccount(e.target.value);
                            setOffset(0);
                          }}
                        >
                          <option value="">All accounts</option>
                          {detail.statement_metadata.accounts.map((a) => (
                            <option key={a.account_id} value={a.account_id}>
                              {a.account_name ?? a.account_id}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="checkbox">
                        <input
                          type="checkbox"
                          checked={needs}
                          onChange={(e) => {
                            setNeeds(e.target.checked);
                            setOffset(0);
                          }}
                        />
                        Needs input
                      </label>
                    </div>
                    {page && (
                      <>
                        <p>
                          {page.total === 0
                            ? "No matching transactions."
                            : `${offset + 1}–${Math.min(offset + 100, page.total)} of ${page.total}`}
                        </p>
                        {groupTransactions(page.rows).map(
                          ([accountId, rows]) => (
                            <section
                              key={accountId}
                              aria-label={`Transactions for ${accountId}`}
                            >
                              <h4>
                                {detail.statement_metadata.accounts.find(
                                  (a) => a.account_id === accountId,
                                )?.account_name ?? accountId}
                              </h4>
                              {rows.map((row) => (
                                <TransactionCard
                                  key={row.record_id}
                                  row={row}
                                  onAnswer={(value, etag) =>
                                    submit({
                                      kind: "answer",
                                      subject_kind: "transaction",
                                      subject_id: row.record_id,
                                      value,
                                      expected_etag: etag,
                                    })
                                  }
                                  etag={page.etag}
                                  disabled={
                                    busy || transactionsUnavailable || done
                                  }
                                  onSave={(value, etag) =>
                                    submit({
                                      kind: "postings",
                                      subject_id: row.record_id,
                                      value,
                                      expected_etag: etag,
                                    })
                                  }
                                />
                              ))}
                            </section>
                          ),
                        )}
                        <div className="actions">
                          <button
                            disabled={offset === 0}
                            onClick={() => setOffset(Math.max(0, offset - 100))}
                          >
                            Previous
                          </button>
                          <button
                            disabled={offset + 100 >= page.total}
                            onClick={() => setOffset(offset + 100)}
                          >
                            Next
                          </button>
                        </div>
                      </>
                    )}
                    {drafts.size > 0 && (
                      <p className="notice">
                        Save or discard unsaved edits before approving this
                        statement.
                      </p>
                    )}
                    {page && page.etag !== detail.etag && (
                      <p className="notice">
                        Statement and transaction views are from different
                        snapshots. Refresh before approval.
                      </p>
                    )}
                    <StatementValidation
                      detail={detail}
                      canApprove={
                        selected?.status === "final_review" &&
                        selected.needs_input === 0
                      }
                      disabled={
                        busy ||
                        unavailable ||
                        transactionsUnavailable ||
                        done ||
                        drafts.size > 0 ||
                        !page ||
                        page.etag !== detail.etag
                      }
                      onDecision={(kind) =>
                        submit({
                          kind,
                          subject_id: "statement",
                          expected_etag: detail.etag,
                          review_digest: detail.review_digest,
                        })
                      }
                    />
                  </>
                )}
              </>
            ) : (
              <SessionPrices
                overview={overview}
                disabled={busy || invalidReads.summary}
                onApprove={approvePrices}
              />
            )}
          </>
        )}
        <footer>
          Local review · Refreshes every 2 seconds while visible · Canonical
          writes require approval
        </footer>
      </main>
    </DraftContext.Provider>
  );
}
