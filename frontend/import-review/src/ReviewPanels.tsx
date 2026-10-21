import type { Detail, Overview } from "./types";
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
}: {
  overview: Overview;
  disabled: boolean;
  onApprove: (runId: string, digest: string) => Promise<void>;
}) {
  return (
    <>
      <h2>Session & prices</h2>
      <p>
        {overview.statements.length} statements ·{" "}
        {overview.statements.reduce((sum, s) => sum + s.needs_input, 0)}{" "}
        outstanding inputs
      </p>
      {overview.price_runs.length === 0 ? (
        <p className="muted">Price results are not available yet.</p>
      ) : (
        overview.price_runs.map((run) => (
          <section className="card" key={run.run_id}>
            <h3>
              {readable(run.state)} · {run.requested_date}
            </h3>
            <p>{run.detail}</p>
            <p>
              Required: {run.required_commodities.join(", ") || "None"} ·
              Preflight: {run.preflight} ({run.preflight_job_count} jobs)
            </p>
            <p>
              Execution: {readable(run.execution.state)} ·{" "}
              {run.execution.duration_seconds}s · Exit{" "}
              {run.execution.exit_code ?? "pending"}
            </p>
            {run.execution.stderr_summary && (
              <details>
                <summary>Execution details</summary>
                <pre>{run.execution.stderr_summary}</pre>
              </details>
            )}
            <p>
              Coverage:{" "}
              {run.coverage.join(", ") ||
                (run.required_commodities.length
                  ? "Unavailable"
                  : "None required")}
            </p>
            <p>
              {["emitted", "redundant", "skipped", "failed", "unaccounted"]
                .map(
                  (outcome) =>
                    `${outcome}: ${run.jobs.filter((job) => job.outcome === outcome).length}`,
                )
                .join(" · ")}
            </p>
            {run.jobs.length === 0 && <p>Zero price jobs.</p>}
            {run.approval?.digest === run.review_digest ? (
              <p>Price panel confirmation saved {run.approval?.approved_at}.</p>
            ) : (
              <p className="muted">
                No panel confirmation. Approval can also be given in
                conversation.
              </p>
            )}
            {run.jobs.some((job) => job.outcome === "emitted") && (
              <button
                disabled={
                  disabled ||
                  !["complete", "partial"].includes(run.state) ||
                  run.approval?.digest === run.review_digest
                }
                onClick={() => void onApprove(run.run_id, run.review_digest)}
              >
                Approve price directives
              </button>
            )}
            {run.validation && run.validation_current === false && (
              <p className="error">
                Stale validation: ledger or reviewed price data changed.
              </p>
            )}
            {run.validation && (
              <p>
                {run.validation.stage === "written"
                  ? "Ledger write validation"
                  : "Review readiness validation"}
                : {run.validation.state} · {run.validation.checked_at}
              </p>
            )}
            {run.jobs.map((j, i) => (
              <div className="price" key={i}>
                <strong>
                  {j.commodity} · {j.outcome}
                </strong>
                <p>
                  {j.source} · Requested {j.requested_date} · Quote{" "}
                  {j.quote_date ?? "unavailable"}
                </p>
                {j.directive && <pre>{j.directive}</pre>}
                {j.detail && <p>{j.detail}</p>}
              </div>
            ))}
          </section>
        ))
      )}
    </>
  );
}
