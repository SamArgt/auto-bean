import { useState, useRef } from "react";
import { SavingIndicator } from "./ReviewForms";
import type { Detail, Overview, PriceRun } from "./types";
const readable = (value: string) => value.replaceAll("_", " ");
export function StatementValidation({
  detail,
  canApprove,
  disabled,
  onDecision,
}: {
  detail: Detail;
  canApprove: boolean;
  disabled: boolean;
  onDecision: (kind: "approve" | "reject") => Promise<boolean>;
}) {
  const approved = detail.approval?.digest === detail.review_digest;
  const validation = detail.validation;
  const stale =
    validation &&
    (validation.digest !== detail.review_digest ||
      detail.validation_current === false);
  return (
    <section className="card" aria-label="Approval and ledger validation">
      <h3>Approval and ledger validation</h3>
      <p>
        Approval covers this statement’s current account mappings, transaction
        postings and dispositions. The import agent writes the ledger, then
        checks every source row and closing balance.
      </p>
      {approved ? (
        <p className="notice">
          Panel confirmation saved {detail.approval?.approved_at}.
        </p>
      ) : (
        <p>
          No panel confirmation. Approval can also be given in conversation.
        </p>
      )}
      {detail.approval && !approved && (
        <p className="notice">
          The reviewed data changed. Review it again before approval.
        </p>
      )}
      <div className="actions">
        <button
          disabled={disabled || !canApprove || approved}
          onClick={() => void onDecision("approve")}
        >
          Approve reviewed transactions
        </button>
        <button
          disabled={disabled || !canApprove}
          onClick={() => void onDecision("reject")}
        >
          Reject
        </button>
      </div>
      {!canApprove && !approved && (
        <p className="muted">
          Approval becomes available when all required input is resolved and the
          statement is ready for review.
        </p>
      )}
      {validation ? (
        <>
          <h4>
            {validation.stage === "written"
              ? "Ledger write validation"
              : "Review readiness validation"}
          </h4>
          {validation.stage === "review" && (
            <p>
              Checks the proposed import. This does not confirm that
              transactions have been written.
            </p>
          )}
          <p
            className={
              validation.state === "failed" || stale ? "error" : "notice"
            }
          >
            {stale
              ? "Stale result: ledger or reviewed data changed."
              : readable(validation.state)}{" "}
            · Checked {validation.checked_at} · {validation.records_checked}{" "}
            source rows checked
          </p>
          {validation.errors.map((error, index) => (
            <p className="error" key={index}>
              {error}
            </p>
          ))}
          {validation.balances.map((balance, index) => (
            <p key={index}>
              {balance.account_id} · {balance.date} · Expected{" "}
              {balance.expected} {balance.currency} · Ledger {balance.actual}{" "}
              {balance.currency} · {balance.state}
            </p>
          ))}
          {!validation.balances.length && (
            <p className="muted">
              {validation.stage === "review"
                ? "Closing balances are checked after ledger writing."
                : "No reported closing balances were available for comparison."}
            </p>
          )}
        </>
      ) : (
        <p className="muted">Validation is not available yet.</p>
      )}
    </section>
  );
}
export function SessionPrices({
  overview,
  disabled,
  onApprove,
  mode = "all",
}: {
  overview: Overview;
  mode?: "all" | "price";
  disabled: boolean;
  onApprove: (runId: string, digest: string) => Promise<void>;
}) {
  return (
    <>
      {mode === "all" && (
        <>
          <h2>Session & prices</h2>
          <p>
            {overview.statements.length} statements ·{" "}
            {overview.statements.reduce((sum, s) => sum + s.needs_input, 0)}{" "}
            outstanding inputs
          </p>
          <h3>Statement groups</h3>
          {overview.groups.map((group) => (
            <section className="card" key={group.group_id}>
              <h4>{group.name}</h4>
              <p>Group status: {readable(group.current_status)}</p>
              <p>{group.origin === "user" ? "User-defined" : "Inferred"}</p>
              <ul>
                {group.source_files.map((source) => (
                  <li key={source}>{source}</li>
                ))}
              </ul>
            </section>
          ))}
        </>
      )}
      {overview.price_runs.length === 0 ? (
        <p className="muted">Price results are not available yet.</p>
      ) : (
        overview.price_runs.map((run) => (
          <PriceCard
            key={run.run_id}
            run={run}
            disabled={disabled}
            onApprove={onApprove}
          />
        ))
      )}
    </>
  );
}

function quoteValue(job: PriceRun["jobs"][number]) {
  const match = job.directive?.match(
    /^\d{4}-\d{2}-\d{2}\s+price\s+(\S+)\s+([+-]?\d+(?:\.\d+)?)\s+(\S+)(?:\s*;.*)?$/,
  );
  return match && match[1] === job.commodity ? `${match[2]} ${match[3]}` : null;
}
const priceOutcome = (value: string) =>
  (
    ({
      emitted: "New price",
      redundant: "Already saved",
      skipped: "Skipped",
      failed: "Fetch failed",
      unaccounted: "Needs review",
    }) as Record<string, string>
  )[value] ?? "Pending";

function PriceCard({
  run,
  disabled,
  onApprove,
}: {
  run: PriceRun;
  disabled: boolean;
  onApprove: (runId: string, digest: string) => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const submitting = useRef(false);
  const approved = run.approval?.digest === run.review_digest;
  const changes = run.jobs.filter((j) => j.outcome === "emitted").length;
  const missing = run.required_commodities.filter(
    (c) => !run.coverage.includes(c),
  );
  const pending = ["pending", "running"].includes(run.state);
  const attention =
    ["failed", "partial"].includes(run.state) ||
    (!pending && missing.length > 0) ||
    run.jobs.some((j) => ["failed", "unaccounted"].includes(j.outcome));
  const status = pending
    ? "Fetching prices"
    : attention
      ? "Needs attention"
      : approved
        ? "Approved"
        : changes
          ? "Ready for review"
          : "No updates needed";
  const newWithoutJob = (run.new_commodities ?? []).filter(
    (c) => !run.jobs.some((j) => j.commodity === c),
  );
  return (
    <section
      className="card price-card"
      aria-label={`Prices for ${run.requested_date}`}
    >
      <header className="price-heading">
        <div>
          <h2>Price update</h2>
          <p className="muted">{run.requested_date}</p>
        </div>
        <span
          className={`badge ${attention ? "warn" : approved ? "received" : ""}`}
        >
          {status}
        </span>
      </header>
      {attention && (
        <p className="notice">
          {run.detail ||
            "Some prices need review before this update is complete."}
        </p>
      )}
      {missing.length > 0 && (
        <p className={pending ? "muted" : "error"}>
          {pending ? "Waiting for quotes" : "Missing prices"}:{" "}
          {missing.join(", ")}
        </p>
      )}
      {run.validation &&
        (run.validation_current === false ||
          run.validation.state === "failed") && (
          <p className="error">
            {run.validation_current === false
              ? "The ledger or prices changed. Validation must run again."
              : "Validation failed. Ask the agent to review this update."}
          </p>
        )}
      {newWithoutJob.length > 0 && (
        <div className="new-commodities" aria-label="New commodities">
          {newWithoutJob.map((c) => (
            <span className="badge warn" key={c}>
              {c} · New commodity
            </span>
          ))}
        </div>
      )}
      {run.jobs.length > 0 ? (
        <div className="table-wrap price-quotes">
          <table>
            <thead>
              <tr>
                <th>Commodity</th>
                <th className="amount">Price</th>
                <th>Quote date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {run.jobs.map((job, i) => (
                <tr
                  key={i}
                  className={`price ${run.new_commodities?.includes(job.commodity) ? "new-commodity" : ""}`}
                >
                  <td>
                    <strong>{job.commodity}</strong>
                    {run.new_commodities?.includes(job.commodity) && (
                      <small>
                        <span className="badge warn">New commodity</span>
                      </small>
                    )}
                  </td>
                  <td className="amount">
                    <strong>{quoteValue(job) ?? "Unavailable"}</strong>
                  </td>
                  <td>
                    {job.quote_date ?? "Unavailable"}
                    {job.quote_date &&
                      job.quote_date !== job.requested_date && (
                        <small className="quote-date-warning">
                          Differs from requested date
                        </small>
                      )}
                  </td>
                  <td>
                    <span
                      className={`badge ${["failed", "unaccounted"].includes(job.outcome) ? "warn" : ""}`}
                    >
                      {priceOutcome(job.outcome)}
                    </span>
                    {["failed", "unaccounted", "skipped"].includes(
                      job.outcome,
                    ) &&
                      job.detail && <small>{job.detail}</small>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty">
          {pending
            ? "Waiting for price results…"
            : "No price updates in this run."}
        </p>
      )}
      {changes > 0 && (
        <div className="price-approval">
          <p>
            {approved
              ? "Approval saved. The agent can apply these prices."
              : `${changes} ${changes === 1 ? "price" : "prices"} to add to your ledger.`}
          </p>
          {saving ? (
            <SavingIndicator />
          ) : (
            <button
              className="primary"
              disabled={
                disabled ||
                approved ||
                !["complete", "partial"].includes(run.state)
              }
              onClick={async () => {
                if (submitting.current) return;
                submitting.current = true;
                setSaving(true);
                try {
                  await onApprove(run.run_id, run.review_digest);
                } finally {
                  submitting.current = false;
                  setSaving(false);
                }
              }}
            >
              {approved ? "Approved" : "Approve prices"}
            </button>
          )}
        </div>
      )}
      <details className="price-details">
        <summary>Sources & technical details</summary>
        <p>{run.detail}</p>
        <p>
          Required: {run.required_commodities.join(", ") || "None"} · Coverage:{" "}
          {run.coverage.join(", ") || "None"}
        </p>
        <p>
          Preflight: {run.preflight} ({run.preflight_job_count} jobs)
        </p>
        <p>
          Execution: {readable(run.execution.state)} ·{" "}
          {run.execution.duration_seconds}s · Exit{" "}
          {run.execution.exit_code ?? "pending"}
        </p>
        {run.execution.stderr_summary && (
          <pre>{run.execution.stderr_summary}</pre>
        )}
        {run.jobs.map((job, i) => (
          <section key={i}>
            <h4>
              {job.commodity} · {priceOutcome(job.outcome)}
            </h4>
            <p>
              Source: {job.source} · Requested {job.requested_date}
            </p>
            {job.directive && <pre>{job.directive}</pre>}
            {job.detail && <p>{job.detail}</p>}
          </section>
        ))}
        {run.approval && <p>Approval saved {run.approval.approved_at}</p>}
        {run.validation && (
          <p>
            {run.validation.stage === "written"
              ? "Ledger write validation"
              : "Review readiness validation"}
            : {run.validation.state} · {run.validation.checked_at}
          </p>
        )}
      </details>
    </section>
  );
}
