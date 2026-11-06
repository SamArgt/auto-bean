import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

export const DraftContext = createContext<(id: string, dirty: boolean) => void>(
  () => {},
);
function useDraft(dirty: boolean) {
  const id = useId();
  const report = useContext(DraftContext);
  useEffect(() => {
    report(id, dirty);
    return () => report(id, false);
  }, [id, dirty, report]);
}
import { categoryLabel, categorySuggestions } from "./suggestions";
import type { Posting, Transaction } from "./types";
const readable = (s: string) => s.replaceAll("_", " ");
const filename = (s: string) => s.split("/").at(-1) ?? s;
export function SavingIndicator() {
  return (
    <span className="saving" role="status">
      <span className="spinner" aria-hidden="true" />
      Applying changes…
    </span>
  );
}
export function TextEdit({
  label,
  value,
  etag,
  suggestions = [],
  choices = [],
  disabled,
  allowConfirm = false,
  categoryChoices = false,
  saveLabel = "Save correction",
  onSave,
  onSearch,
}: {
  label: string;
  value: string;
  etag: string;
  suggestions?: string[];
  choices?: string[];
  disabled: boolean;
  allowConfirm?: boolean;
  categoryChoices?: boolean;
  saveLabel?: string;
  onSave: (value: string, etag: string) => Promise<boolean>;
  onSearch?: (value: string) => void;
}) {
  const [edit, setEdit] = useState<string | null>(null),
    [base, setBase] = useState(etag);
  const [custom, setCustom] = useState(false);
  const [pending, setPending] = useState(false);
  const submitting = useRef(false);
  disabled = disabled || pending;
  const dirty = edit !== null;
  useDraft(dirty);
  return (
    <form
      className={choices.length ? "choice-form" : undefined}
      onSubmit={async (e) => {
        e.preventDefault();
        if (submitting.current) return;
        submitting.current = true;
        setPending(true);
        const submitted = edit ?? value;
        try {
          if (await onSave(submitted, dirty ? base : etag))
            setEdit((current) => (current === submitted ? null : current));
        } finally {
          submitting.current = false;
          setPending(false);
        }
      }}
    >
      {categoryChoices && choices.length > 0 && (
        <fieldset className="category-options">
          <legend>Suggested categories</legend>
          {choices.map((choice, index) => (
            <label key={choice}>
              <input
                type="radio"
                name={label}
                value={choice}
                checked={edit === choice}
                disabled={disabled}
                onChange={() => {
                  if (!dirty) setBase(etag);
                  setCustom(false);
                  setEdit(choice);
                }}
              />
              <span>
                {categoryLabel(choice)}
                {index === 0 && <small>Most likely</small>}
              </span>
            </label>
          ))}
          <label>
            <input
              type="radio"
              name={label}
              checked={custom}
              disabled={disabled}
              onChange={() => {
                if (!dirty) setBase(etag);
                setCustom(true);
                setEdit("");
              }}
            />
            Something else
          </label>
        </fieldset>
      )}
      {!categoryChoices && choices.length > 0 && (
        <label className="choice-options">
          {label} suggestions
          <select
            aria-label={`${label} choices`}
            disabled={disabled}
            value={
              custom || (edit !== null && !choices.includes(edit))
                ? "__custom"
                : (edit ?? "")
            }
            onChange={(e) => {
              if (!dirty) setBase(etag);
              const value = e.target.value;
              setCustom(value === "__custom");
              setEdit(value === "__custom" ? "" : value);
            }}
          >
            <option value="" disabled>
              Choose a suggestion
            </option>
            {choices.map((choice) => (
              <option key={choice} value={choice}>
                {choice}
              </option>
            ))}
            <option value="__custom">Something else</option>
          </select>
        </label>
      )}
      <label
        className="choice-custom"
        hidden={
          choices.length > 0 &&
          !custom &&
          (edit === null || choices.includes(edit))
        }
      >
        {label}
        <input
          aria-label={label}
          disabled={disabled}
          placeholder={
            choices.length
              ? "Choose a suggestion or enter a correction"
              : undefined
          }
          value={edit ?? value}
          onFocus={() => onSearch?.(edit ?? value)}
          onChange={(e) => {
            if (!dirty) setBase(etag);
            setEdit(e.target.value);
            onSearch?.(e.target.value);
          }}
        />
      </label>
      {suggestions.length > 0 && (
        <select
          aria-label={`${label} suggestions`}
          value=""
          disabled={disabled}
          onChange={(e) => {
            if (!dirty) setBase(etag);
            setEdit(e.target.value);
          }}
        >
          <option value="">Choose a suggestion</option>
          {suggestions.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      )}
      {dirty && base !== etag && (
        <p role="status" className="notice">
          This review changed while you were editing. Your edit is preserved.{" "}
          <button type="button" onClick={() => setBase(etag)}>
            Use refreshed data
          </button>
        </p>
      )}
      <div className="actions">
        <button
          className={choices.length ? "primary" : undefined}
          disabled={
            disabled || (!dirty && !allowConfirm) || !(edit ?? value).trim()
          }
          type="submit"
        >
          {pending
            ? "Saving…"
            : allowConfirm && !dirty
              ? "Confirm mapping"
              : choices.length &&
                  !custom &&
                  (edit === null || choices.includes(edit))
                ? "Save choice"
                : saveLabel}
        </button>
        {dirty && (
          <button
            type="button"
            disabled={pending}
            onClick={() => {
              setEdit(null);
              setCustom(false);
            }}
          >
            Discard edit
          </button>
        )}
      </div>
      {pending && !categoryChoices && <SavingIndicator />}
      {choices.length > 0 && value && edit === null && (
        <p className="saved-answer">Saved answer: {value}</p>
      )}
    </form>
  );
}
export function TransactionCard({
  row,
  etag,
  disabled,
  onSave,
  onAnswer,
  onLink,
  navigationDisabled = false,
  received = false,
}: {
  row: Transaction;
  received?: boolean;
  onLink?: (source: string, account: string, record: string) => void;
  navigationDisabled?: boolean;
  etag: string;
  disabled: boolean;
  onSave: (p: Posting[], r: string) => Promise<boolean>;
  onAnswer: (value: string, etag: string) => Promise<boolean>;
}) {
  const [edit, setEdit] = useState<Posting[] | null>(null),
    [base, setBase] = useState(etag);
  useDraft(edit !== null);
  const r = row,
    d = row.review,
    needs = d?.state === "needs_input" || d?.disposition === "hold";
  const choices = categorySuggestions(d?.suggestions);
  return (
    <section className={`card ${needs && !received ? "needs" : ""}`}>
      <h4>
        {received && needs
          ? "✓ Input received · "
          : needs
            ? "⚠ Needs input · "
            : ""}
        {r.description}
      </h4>
      <p>
        {r.transaction_date} ·{" "}
        <strong>
          {r.amount} {r.currency}
        </strong>{" "}
        · {r.account_id}
      </p>
      <p className="rationale">
        {d?.rationale ?? "Rationale is not available yet."}
      </p>
      {received && needs && (
        <p className="received-note">Saved for agent review.</p>
      )}
      <p>{d ? readable(d.disposition) : "Categorization pending"}</p>
      {d?.postings.map((p, i) => (
        <p key={i}>
          {p.account}{" "}
          <strong>
            {p.amount} {p.currency}
          </strong>
          {p.cost ? ` ${p.cost}` : ""}
          {p.price ? ` ${p.price}` : ""}
        </p>
      ))}
      <details>
        <summary>Evidence & rationale</summary>
        <p>
          {r.source_reference} · {r.record_id}
        </p>

        {d?.suggestions?.some((s) => !choices.includes(s)) && (
          <p>{d.suggestions.filter((s) => !choices.includes(s)).join(" · ")}</p>
        )}
        <p>{d?.findings?.map(readable).join(", ")}</p>
        {d?.existing_transaction && (
          <div>
            <p>
              Existing ledger transaction: {d.existing_transaction.path} · Line{" "}
              {d.existing_transaction.line}
            </p>
          </div>
        )}
        {d?.linked_records?.map((l, i) => (
          <p key={i}>
            {onLink ? (
              <button
                disabled={navigationDisabled}
                onClick={() => onLink(l.source_file, l.account_id, l.record_id)}
              >
                Follow transfer · {filename(l.source_file)} · {l.account_id}
              </button>
            ) : (
              `${filename(l.source_file)} · ${l.account_id}`
            )}{" "}
            · {l.record_id}
          </p>
        ))}
      </details>
      {needs && d && (
        <TextEdit
          label="Transaction answer"
          choices={choices}
          categoryChoices
          value={d.answer ?? ""}
          etag={etag}
          disabled={disabled}
          saveLabel="Save answer"
          onSave={onAnswer}
        />
      )}
      {!needs && d?.answer && <p>Saved answer: {d.answer}</p>}
      {d?.disposition === "paired_transfer" && (
        <p className="notice">
          Shared transfer postings are read-only. Posting owner:{" "}
          {d.posting_owner ?? "unavailable"}. Ask the agent to review a
          correction.
        </p>
      )}
      {d && d.disposition !== "paired_transfer" && !edit && (
        <button
          disabled={disabled}
          onClick={() => {
            setEdit(d.postings.map((p) => ({ ...p })));
            setBase(etag);
          }}
        >
          Correct postings
        </button>
      )}
      {edit && (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            const submitted = edit;
            if (await onSave(submitted, base))
              setEdit((current) => (current === submitted ? null : current));
          }}
        >
          {edit.map((p, i) => (
            <fieldset key={i}>
              <legend>Posting {i + 1}</legend>
              {(
                ["account", "amount", "currency", "cost", "price"] as const
              ).map((field) => (
                <label key={field}>
                  {readable(field)}
                  <input
                    required={["account", "amount", "currency"].includes(field)}
                    value={p[field] ?? ""}
                    onChange={(e) =>
                      setEdit(
                        edit.map((v, j) =>
                          j === i ? { ...v, [field]: e.target.value } : v,
                        ),
                      )
                    }
                  />
                </label>
              ))}
              <button
                type="button"
                onClick={() => setEdit(edit.filter((_, j) => j !== i))}
              >
                Remove posting
              </button>
            </fieldset>
          ))}
          <button
            type="button"
            onClick={() =>
              setEdit([
                ...edit,
                { account: "", amount: "", currency: r.currency },
              ])
            }
          >
            Add split posting
          </button>
          {base !== etag && (
            <p className="notice">
              Review changed; edits preserved.{" "}
              <button type="button" onClick={() => setBase(etag)}>
                Use refreshed data
              </button>
            </p>
          )}
          <div className="actions">
            <button disabled={disabled || !edit.length}>Save correction</button>
            <button type="button" onClick={() => setEdit(null)}>
              Discard edit
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
