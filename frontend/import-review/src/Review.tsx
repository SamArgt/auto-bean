import { useCallback, useEffect, useRef, useState } from "react";
import { DraftContext } from "./ReviewForms";
import { StatementValidation, SessionPrices } from "./ReviewPanels";
import { TransactionTable } from "./TransactionTable";
import { StatementEvidence } from "./StatementEvidence";
import { SessionOverview } from "./SessionOverview";
import { ReviewExport } from "./ReviewExport";
export { TextEdit } from "./ReviewForms";
import type {
  ReviewUpdate,
  ReviewBatch,
  SavedReview,
  SavedPrice,
  Binding,
  Bridge,
  Detail,
  Overview,
  Page,
} from "./types";

const readable = (s: string) => s.replaceAll("_", " ");
const filename = (s: string) => s.split("/").at(-1) ?? s;
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
  const [focusRecord, setFocusRecord] = useState<{ record_id: string } | null>(
    null,
  );
  const [view, setView] = useState<"session" | "account" | "price">("session");
  const [catalog, setCatalog] = useState<Record<string, Detail>>({});
  const [accountNeeds, setAccountNeeds] = useState<
    Record<string, number | null>
  >({});
  const [catalogErrors, setCatalogErrors] = useState<Record<string, string>>(
    {},
  );
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
  const [notified, setNotified] = useState<ReviewBatch | null>(null),
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
      if (summary.status === "fulfilled") {
        setOverview(summary.value);
        const sources = summary.value.statements.map((s) => s.source_file);
        const details = await Promise.allSettled(
          sources.map((file) =>
            file === source && d.status === "fulfilled" && d.value
              ? Promise.resolve(d.value)
              : bridge.call<Detail>("read_import_statement", {
                  ...binding,
                  source_file: file,
                }),
          ),
        );
        if (!current()) return;
        const errors: Record<string, string> = {};
        setCatalog((previous) => {
          const next: Record<string, Detail> = {};
          sources.forEach((file, i) => {
            const result = details[i];
            if (result.status === "fulfilled") next[file] = result.value;
            else {
              if (previous[file]) next[file] = previous[file];
            }
          });
          return next;
        });
        // Compute failures outside the state updater, which React may defer.
        sources.forEach((file, i) => {
          const result = details[i];
          if (result.status === "rejected")
            errors[file] = String(result.reason);
        });
        setCatalogErrors(errors);
      }
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
  useEffect(() => {
    if (!binding) return;
    let cancelled = false;
    const accounts = Object.entries(catalog).flatMap(([file, detail]) =>
      detail.statement_metadata.accounts.map((account) => ({ file, account })),
    );
    void Promise.allSettled(
      accounts.map(({ file, account }) =>
        bridge.call<Page>("list_import_transactions", {
          ...binding,
          source_file: file,
          account_id: account.account_id,
          offset: 0,
          limit: 1,
          needs_input: true,
        }),
      ),
    ).then((results) => {
      if (cancelled) return;
      setAccountNeeds(
        Object.fromEntries(
          accounts.map(({ file, account }, i) => {
            const result = results[i];
            return [
              JSON.stringify([file, account.account_id]),
              result.status === "fulfilled"
                ? result.value.total +
                  (account.review?.state === "needs_input" ? 1 : 0)
                : null,
            ];
          }),
        ),
      );
    });
    return () => {
      cancelled = true;
    };
  }, [bridge, binding, catalog]);
  async function sendBatch() {
    if (
      !binding ||
      !overview ||
      activeSubmission.current ||
      drafts.size ||
      loadError ||
      (!notified && !overview?.review_batch?.ready)
    )
      return;
    activeSubmission.current = true;
    setBusy(true);
    try {
      const batch =
        notified ??
        (await bridge.call<ReviewBatch>("prepare_import_review_batch", {
          ...binding,
          token: overview.review_batch.token,
        }));
      if (!notified) {
        await bridge.continue(binding.session_id, batch.subjects);
        setNotified(batch);
      }
      await bridge.call<ReviewBatch>("acknowledge_import_review_batch", {
        ...binding,
        pending_token: batch.pending_token,
      });
      setNotified(null);
      setNotice(
        "Saved changes sent. The agent will read the JSON and continue the import.",
      );
      await refresh();
    } catch (e) {
      setNotice(
        `Changes remain saved. Send failed: ${String(e)}. Refresh before retrying.`,
      );
      await refresh();
    } finally {
      activeSubmission.current = false;
      setBusy(false);
    }
  }
  async function submit(update: ReviewUpdate) {
    if (!binding || !source || activeSubmission.current) return false;
    activeSubmission.current = true;
    setBusy(true);
    setError("");
    try {
      await bridge.call<SavedReview>("update_import_review", {
        ...binding,
        source_file: source,
        update,
      });
      setNotice(
        "Saved to JSON. Send saved changes when the current review is complete.",
      );
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
      await bridge.call<SavedPrice>("approve_import_prices", {
        ...binding,
        run_id: runId,
        expected_etag: overview.etag,
        review_digest: digest,
      });
      setNotice("Price approval saved to JSON. Agent not notified.");
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
    !selected || invalidReads.summary || invalidReads.detail || selected?.error,
  );
  const transactionsUnavailable = Boolean(
    !selected || invalidReads.summary || invalidReads.page || selected?.error,
  );
  function navigate(
    nextView: typeof view,
    nextSource: string | null = null,
    nextAccount = "",
  ) {
    if (drafts.size || busy) return;
    setFocusRecord(null);
    setView(nextView);
    if (source !== nextSource) {
      setDetail(null);
      setPage(null);
    }
    if (account !== nextAccount) setPage(null);
    setSource(nextSource);
    setAccount(nextAccount);
    setOffset(0);
    setNeeds(false);
    setError("");
  }
  async function followTransfer(
    file: string,
    accountId: string,
    recordId: string,
  ) {
    if (!binding || drafts.size || activeSubmission.current) return;
    const key = queryKey;
    activeSubmission.current = true;
    setBusy(true);
    setError("");
    try {
      let nextOffset = 0;
      while (latestQuery.current === key) {
        const result = await bridge.call<Page>("list_import_transactions", {
          ...binding,
          source_file: file,
          account_id: accountId,
          offset: nextOffset,
          limit: 100,
          needs_input: false,
        });
        if (latestQuery.current !== key) return;
        if (result.rows.some((row) => row.record_id === recordId)) {
          navigate("account", file, accountId);
          setOffset(nextOffset);
          setFocusRecord({ record_id: recordId });
          return;
        }
        nextOffset += 100;
        if (nextOffset >= result.total)
          throw Error(
            "The linked transaction is no longer available. Refresh and ask the agent to review the transfer.",
          );
      }
    } catch (e) {
      if (latestQuery.current === key) setError(String(e));
    } finally {
      activeSubmission.current = false;
      setBusy(false);
    }
  }
  const statementContent = source ? (
    <section key={source} className="statement-detail">
      <h2>
        {view === "account"
          ? (detail?.statement_metadata.accounts.find(
              (a) => a.account_id === account,
            )?.account_name ?? "Transactions")
          : filename(source)}
      </h2>
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
          {view === "session" && (
            <StatementEvidence
              detail={detail}
              disabled={busy || unavailable || done}
              accounts={accounts}
              onSearch={search}
              onSubmit={submit}
            />
          )}
          {view === "account" && (
            <>
              <div className="filters">
                <label>
                  Account
                  <select
                    aria-label="Account"
                    value={account}
                    disabled={!!drafts.size}
                    onChange={(e) =>
                      navigate("account", source, e.target.value)
                    }
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
                    disabled={!!drafts.size}
                    onChange={(e) => {
                      setNeeds(e.target.checked);
                      setOffset(0);
                    }}
                  />
                  Needs input
                </label>
              </div>
              {page && (
                <TransactionTable
                  key={`${source}:${account}:${needs}:${offset}`}
                  page={page}
                  source={source}
                  focusRecord={focusRecord}
                  disabled={busy || transactionsUnavailable || done}
                  navigationDisabled={!!drafts.size || busy}
                  onLink={(file, id, record) =>
                    void followTransfer(file, id, record)
                  }
                  onAnswer={(row, value, etag) =>
                    submit({
                      kind: "answer",
                      subject_kind: "transaction",
                      subject_id: row.record_id,
                      value,
                      expected_etag: etag,
                    })
                  }
                  onSave={(row, value, etag) =>
                    submit({
                      kind: "postings",
                      subject_id: row.record_id,
                      value,
                      expected_etag: etag,
                    })
                  }
                />
              )}
              {page && (
                <div className="actions pagination">
                  <span>
                    {page.total === 0
                      ? "No matching transactions."
                      : `${offset + 1}–${Math.min(offset + 100, page.total)} of ${page.total}`}
                  </span>
                  <button
                    disabled={offset === 0 || !!drafts.size || busy}
                    onClick={() => setOffset(Math.max(0, offset - 100))}
                  >
                    Previous
                  </button>
                  <button
                    disabled={
                      !page ||
                      offset + 100 >= page.total ||
                      !!drafts.size ||
                      busy
                    }
                    onClick={() => setOffset(offset + 100)}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
          {drafts.size > 0 && (
            <p className="notice">
              Save or discard unsaved edits before approving this statement.
            </p>
          )}
          {page && page.etag !== detail.etag && (
            <p className="notice">
              Statement and transaction views are from different snapshots.
              Refresh before approval.
            </p>
          )}
          {view === "session" && (
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
          )}
        </>
      )}
    </section>
  ) : null;
  return (
    <DraftContext.Provider value={reportDraft}>
      <div className="review-app">
        <header className="app-header">
          <div>
            <span className="eyebrow">AUTO BEAN</span>
            <h1>Import review</h1>
          </div>
          <button onClick={() => void refresh()} disabled={!binding}>
            Refresh
          </button>
        </header>
        <div className="workspace-layout">
          {overview && (
            <aside className="sidebar">
              <p className="eyebrow">IMPORT WORKSPACE</p>
              <nav aria-label="Review navigation">
                <button
                  aria-current={view === "session" ? "page" : undefined}
                  disabled={!!drafts.size || busy}
                  onClick={() => navigate("session")}
                >
                  Session
                </button>
                <button
                  aria-current={view === "account" ? "page" : undefined}
                  disabled={!!drafts.size || busy}
                  onClick={() =>
                    navigate(
                      "account",
                      source ?? overview.statements[0]?.source_file ?? null,
                    )
                  }
                >
                  Account
                </button>
                <div className="account-nav">
                  {overview.statements.flatMap((s) =>
                    (
                      catalog[s.source_file]?.statement_metadata.accounts ?? []
                    ).map((a) => (
                      <button
                        className="sidebar-account"
                        key={`${s.source_file}:${a.account_id}`}
                        aria-current={
                          view === "account" &&
                          source === s.source_file &&
                          account === a.account_id
                            ? "page"
                            : undefined
                        }
                        disabled={!!drafts.size || busy}
                        onClick={() =>
                          navigate("account", s.source_file, a.account_id)
                        }
                      >
                        <span>
                          <strong>{a.account_name ?? a.account_id}</strong>
                          <small>{filename(s.source_file)}</small>
                        </span>
                        {accountNeeds[
                          JSON.stringify([s.source_file, a.account_id])
                        ] ? (
                          <span
                            className="badge warn"
                            title="Outstanding account and transaction inputs"
                          >
                            {
                              accountNeeds[
                                JSON.stringify([s.source_file, a.account_id])
                              ]
                            }
                          </span>
                        ) : accountNeeds[
                            JSON.stringify([s.source_file, a.account_id])
                          ] === null ? (
                          <span
                            className="badge"
                            title="Input count unavailable"
                          >
                            ?
                          </span>
                        ) : null}
                      </button>
                    )),
                  )}
                  {!Object.keys(catalog).length && (
                    <p className="muted">
                      Account evidence is not available yet.
                    </p>
                  )}
                </div>
                <button
                  aria-current={view === "price" ? "page" : undefined}
                  disabled={!!drafts.size || busy}
                  onClick={() => navigate("price")}
                >
                  Price
                </button>
              </nav>
            </aside>
          )}
          <main>
            {binding && (
              <details className="export-panel">
                <summary>Export saved review</summary>
                <ReviewExport
                  key={`${binding.workspace}:${binding.session_id}`}
                  bridge={bridge}
                  binding={binding}
                />
              </details>
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
                    disabled={!!drafts.size || busy}
                    onClick={() => {
                      setNotified(null);
                      setBinding(null);
                      setOverview(null);
                      setCatalog({});
                      setCatalogErrors({});
                      setView("session");
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
                  Displayed results may be stale. Related actions are paused
                  until a successful refresh.
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
              </div>
            )}
            {overview && (
              <>
                <div className="title">
                  <div>
                    <p className="eyebrow">IMPORT REVIEW</p>
                    <h1>
                      {view === "session"
                        ? "Session"
                        : view === "price"
                          ? "Price"
                          : "Account"}
                    </h1>
                  </div>
                  <span className="badge">
                    {overview.statements.length} statements ·{" "}
                    {overview.statements.reduce(
                      (sum, item) => sum + item.needs_input,
                      0,
                    )}{" "}
                    outstanding inputs
                  </span>
                </div>
                {view === "session" && (
                  <SessionOverview
                    selectedDetail={statementContent}
                    overview={overview}
                    catalog={catalog}
                    errors={catalogErrors}
                    disabled={!!drafts.size || busy}
                    selected={source}
                    onSource={(file) => navigate("session", file)}
                    onAccount={(file, id) => navigate("account", file, id)}
                  />
                )}
                {view === "account" && statementContent}
                {view === "account" && !source && (
                  <p className="empty">
                    Choose a source account when statement evidence is
                    available.
                  </p>
                )}
                {view === "price" ? (
                  <SessionPrices
                    overview={overview}
                    disabled={busy || invalidReads.summary}
                    onApprove={approvePrices}
                    mode="price"
                  />
                ) : null}
                <footer className="review-footer" aria-label="Saved changes">
                  <div>
                    <strong>
                      {overview.review_batch?.pending_count ?? 0} saved changes
                    </strong>
                    <p>
                      {overview.review_batch?.blockers.length
                        ? `${overview.review_batch.blockers.length} current inputs still need review.`
                        : "All current required inputs reviewed."}
                    </p>
                    {!!overview.review_batch?.blockers.length && (
                      <details>
                        <summary>Remaining inputs</summary>
                        <ul>
                          {overview.review_batch.blockers.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                  <button
                    className="primary"
                    disabled={
                      busy ||
                      !!drafts.size ||
                      !!loadError ||
                      (!notified && !overview.review_batch?.ready)
                    }
                    onClick={() => void sendBatch()}
                  >
                    {notified ? "Finish sent batch" : "Send saved changes"}
                  </button>
                  {!!drafts.size && (
                    <p>Save or discard unsaved edits before sending.</p>
                  )}
                </footer>
              </>
            )}
            {!!drafts.size && (
              <p className="notice" role="status">
                Save or discard unsaved edits before changing views, filters, or
                sending.
              </p>
            )}
            <p className="subtle">
              Local review · Refreshes every 2 seconds while visible · Canonical
              writes require approval
            </p>
          </main>
        </div>
      </div>
    </DraftContext.Provider>
  );
}
