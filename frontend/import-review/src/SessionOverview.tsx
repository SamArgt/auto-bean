import type { ReactNode } from "react";
import type { Detail, Overview } from "./types";
const readable = (s: string) => s.replaceAll("_", " ");
const filename = (s: string) => s.split("/").at(-1) ?? s;

/** Summary evidence comes from the same statement tools as the detail view. */
export function SessionOverview({
  overview,
  catalog,
  errors,
  selected,
  selectedDetail,
  disabled,
  onSource,
  onAccount,
}: {
  overview: Overview;
  catalog: Record<string, Detail>;
  errors: Record<string, string>;
  selected: string | null;
  selectedDetail: ReactNode;
  disabled: boolean;
  onSource: (source: string) => void;
  onAccount: (source: string, account: string) => void;
}) {
  return (
    <section aria-label="Statement groups">
      {overview.groups.length === 0 && (
        <p className="empty">No imports available for review.</p>
      )}
      {overview.groups.map((group) => (
        <details className="group" key={group.group_id} open>
          <summary>
            <div>
              <strong>{group.name}</strong>
              <small>
                {group.source_files.length}{" "}
                {group.source_files.length === 1 ? "statement" : "statements"}
              </small>
            </div>
            <span className="badge">
              {group.current_status === "done"
                ? "Imported"
                : group.current_status === "final_review"
                  ? "Ready for approval"
                  : group.current_status.endsWith("_blocked")
                    ? "Review needed"
                    : "In progress"}
            </span>
          </summary>
          {group.source_files.map((file) => {
            const statement = overview.statements.find(
              (s) => s.source_file === file,
            );
            const detail = catalog[file];
            const failure = errors[file] ?? statement?.error;
            return (
              <section className="statement" key={file}>
                <div className="statement-head">
                  <div>
                    <button
                      className="row-button"
                      aria-pressed={selected === file}
                      disabled={disabled}
                      onClick={() => onSource(file)}
                    >
                      {filename(file)}
                    </button>
                    {(!detail || detail.extraction_state !== "complete") && (
                      <small>
                        {detail
                          ? `Extraction ${readable(detail.extraction_state)}`
                          : "Loading statement…"}
                      </small>
                    )}
                  </div>
                  {statement?.needs_input ||
                  statement?.status === "done" ||
                  statement?.status === "final_review" ? (
                    <span
                      className={`badge ${statement?.needs_input ? "warn" : ""}`}
                    >
                      {statement?.needs_input
                        ? `${statement.needs_input} need input`
                        : statement?.status === "done"
                          ? "Imported"
                          : "Ready for approval"}
                    </span>
                  ) : null}
                </div>
                {failure && (
                  <p className="error" role="alert">
                    Statement unavailable: {failure}. Refresh to retry.
                  </p>
                )}
                {detail?.statement_metadata.accounts.map((a) => (
                  <div className="account-row" key={a.account_id}>
                    <div>
                      <button
                        className="account-link"
                        disabled={disabled || !!failure}
                        onClick={() => onAccount(file, a.account_id)}
                      >
                        {a.account_name ?? a.account_id}
                      </button>
                      <small>
                        {a.review?.ledger_account ?? "Mapping pending"}
                      </small>
                    </div>
                    {(["opening_balance", "closing_balance"] as const).map(
                      (key) => (
                        <div className="balance" key={key}>
                          <small>{readable(key)}</small>
                          <strong>
                            {a[key]
                              ? `${a[key].amount} ${a[key].currency}`
                              : "Unavailable"}
                          </strong>
                          {a[key] && <small>{a[key].date}</small>}
                        </div>
                      ),
                    )}
                    <div>
                      <span
                        className={`badge ${a.review?.state === "needs_input" ? "warn" : ""}`}
                      >
                        {detail.received_inputs?.includes(
                          "account:" + a.account_id,
                        )
                          ? "Input received"
                          : a.review?.state === "needs_input"
                            ? "Needs input"
                            : a.review?.state === "confirmed"
                              ? "Mapped"
                              : "Mapping pending"}
                      </span>
                    </div>
                  </div>
                ))}
                {detail && !detail.statement_metadata.accounts.length && (
                  <p className="muted">
                    Account evidence is not available yet.
                  </p>
                )}
                <div className="approval">
                  <span>
                    {detail?.approval?.digest === detail?.review_digest &&
                    detail?.approval
                      ? "Approval saved"
                      : ""}
                  </span>
                  <button
                    disabled={disabled || !!failure}
                    onClick={() => onSource(file)}
                  >
                    Review statement
                  </button>
                </div>
                {selected === file && selectedDetail}
              </section>
            );
          })}
        </details>
      ))}
    </section>
  );
}
