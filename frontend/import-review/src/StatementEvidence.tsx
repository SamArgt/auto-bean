import { TextEdit } from "./ReviewForms";
import type { Detail, ReviewUpdate } from "./types";
const readable = (s: string) => s.replaceAll("_", " ");
export function StatementEvidence({
  detail,
  disabled,
  accounts,
  onSearch,
  onSubmit,
}: {
  detail: Detail;
  disabled: boolean;
  accounts: string[];
  onSearch: (query: string) => void;
  onSubmit: (update: ReviewUpdate) => Promise<boolean>;
}) {
  return (
    <>
      <p>Extraction: {readable(detail.extraction_state)}</p>
      {detail.processing.failure_reason && (
        <p className="error">{detail.processing.failure_reason}</p>
      )}
      {detail.processing.warnings.map((w, i) => (
        <p className="notice" key={i}>
          {w}
        </p>
      ))}
      {detail.processing.needs_input && (
        <section className="card needs">
          <h3>⚠ Processing needs input</h3>
          <TextEdit
            label="Processing answer"
            choices={detail.processing.suggestions}
            value={detail.processing.answer ?? ""}
            etag={detail.etag}
            disabled={disabled}
            saveLabel="Save answer"
            onSave={(value, etag) =>
              onSubmit({
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
      {!detail.processing.needs_input && detail.processing.answer && (
        <p>Saved processing answer: {detail.processing.answer}</p>
      )}
      <h3>Accounts & balances</h3>
      {detail.statement_metadata.accounts.length === 0 ? (
        <p className="muted">Account evidence is not available yet.</p>
      ) : (
        detail.statement_metadata.accounts.map((a) => {
          const d = a.review;
          return (
            <section
              className={`card ${d?.state === "needs_input" ? "needs" : ""}`}
              key={a.account_id}
            >
              <h4>
                {d?.state === "needs_input" ? "⚠ Needs input · " : ""}
                {a.account_name ?? a.account_id}
              </h4>
              {a.account_owner && <p>{a.account_owner}</p>}
              <p>{d?.rationale ?? "Mapping proposal not available yet."}</p>
              {d?.answer && <p>Saved answer: {d.answer}</p>}
              {d && (
                <TextEdit
                  label="Ledger mapping"
                  value={d.ledger_account ?? ""}
                  etag={detail.etag}
                  suggestions={[
                    ...new Set([
                      ...(d.suggestions ?? []).filter((s) =>
                        /^(Assets|Liabilities|Equity|Income|Expenses):/.test(s),
                      ),
                      ...accounts,
                    ]),
                  ]}
                  onSearch={onSearch}
                  disabled={disabled}
                  allowConfirm={d.state === "needs_input"}
                  onSave={(value, etag) =>
                    onSubmit({
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
                    choices={d.suggestions}
                    value={d.answer ?? ""}
                    etag={detail.etag}
                    disabled={disabled}
                    saveLabel="Save answer"
                    onSave={(value, etag) =>
                      onSubmit({
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
                  Ledger {r.ledger_amount ?? "unavailable"} {r.currency} on{" "}
                  {r.date} · {readable(r.state)}
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
    </>
  );
}
