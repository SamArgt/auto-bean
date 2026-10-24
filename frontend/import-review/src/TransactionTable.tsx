import { useEffect, useRef, useState } from "react";
import { TransactionCard } from "./ReviewForms";
import type { Page, Posting, Transaction } from "./types";
const readable = (s: string) => s.replaceAll("_", " ");

export function TransactionTable({
  page,
  source,
  focusRecord,
  disabled,
  navigationDisabled,
  onLink,
  onAnswer,
  onSave,
}: {
  page: Page;
  source: string;
  focusRecord?: { record_id: string } | null;
  disabled: boolean;
  navigationDisabled: boolean;
  onLink: (source: string, account: string, record: string) => void;
  onAnswer: (row: Transaction, value: string, etag: string) => Promise<boolean>;
  onSave: (
    row: Transaction,
    value: Posting[],
    etag: string,
  ) => Promise<boolean>;
}) {
  const [query, setQuery] = useState("");
  const [transfers, setTransfers] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [openedRow, setOpenedRow] = useState<Transaction | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const handledFocus = useRef<typeof focusRecord>(null);
  const currentRow = page.rows.find((r) => r.record_id === selected);
  const row =
    currentRow ?? (openedRow?.record_id === selected ? openedRow : null);
  useEffect(() => {
    if (currentRow) setOpenedRow(currentRow);
  }, [currentRow]);
  useEffect(() => {
    if (focusRecord && focusRecord !== handledFocus.current) {
      handledFocus.current = focusRecord;
      setSelected(focusRecord.record_id);
      setOpenedRow(
        page.rows.find((r) => r.record_id === focusRecord.record_id) ?? null,
      );
    }
  }, [focusRecord, page.rows]);
  useEffect(() => {
    if (selected && !dialog.current?.open) dialog.current?.showModal();
  }, [selected]);
  function close() {
    if (navigationDisabled) return;
    dialog.current?.close();
    setSelected(null);
    setOpenedRow(null);
    opener.current?.focus();
  }
  const rows = page.rows.filter(
    (r) =>
      (!transfers ||
        r.review?.disposition === "paired_transfer" ||
        r.review?.findings?.includes("likely_transfer")) &&
      `${r.description} ${r.transaction_date} ${r.amount} ${r.review?.postings.map((p) => p.account).join(" ") ?? ""}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <>
      <div className="toolbar">
        <button
          aria-pressed={transfers}
          disabled={navigationDisabled}
          onClick={() => setTransfers((v) => !v)}
        >
          Internal transfers
        </button>
        <label className="search-label">
          Search this page
          <input
            type="search"
            value={query}
            disabled={navigationDisabled}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search transactions…"
          />
        </label>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Transaction</th>
              <th>Category / status</th>
              <th className="amount">Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const needs =
                r.review?.state === "needs_input" ||
                r.review?.disposition === "hold";
              return (
                <tr key={r.record_id} className={needs ? "needs" : ""}>
                  <td>{r.transaction_date}</td>
                  <td>
                    <button
                      className="row-button"
                      disabled={navigationDisabled}
                      onClick={(e) => {
                        opener.current = e.currentTarget;
                        setSelected(r.record_id);
                        setOpenedRow(r);
                      }}
                    >
                      {r.description}
                    </button>
                    <small>{r.source_reference}</small>
                  </td>
                  <td>
                    {needs ? (
                      <span className="badge warn">Needs input</span>
                    ) : (
                      readable(
                        r.review?.disposition ?? "Categorization pending",
                      )
                    )}
                    <small>
                      {r.review?.postings.map((p) => p.account).join(" · ")}
                    </small>
                  </td>
                  <td className="amount">
                    {r.amount} {r.currency}
                  </td>
                </tr>
              );
            })}
            {!rows.length && (
              <tr>
                <td colSpan={4} className="empty">
                  No matching transactions on this page.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <dialog
        ref={dialog}
        aria-label="Transaction review"
        onCancel={(e) => {
          e.preventDefault();
          close();
        }}
      >
        <button
          className="close"
          aria-label="Close transaction"
          disabled={navigationDisabled}
          onClick={close}
        >
          ×
        </button>
        {row && !currentRow && (
          <p className="notice" role="status">
            This transaction left the current page. Your draft is preserved.
            Discard it and refresh before continuing.
          </p>
        )}
        {row ? (
          <TransactionCard
            key={`${source}:${row.record_id}`}
            row={row}
            etag={page.etag}
            disabled={disabled || !currentRow}
            onAnswer={(value, etag) => onAnswer(row, value, etag)}
            onSave={(value, etag) => onSave(row, value, etag)}
            onLink={onLink}
            navigationDisabled={navigationDisabled}
          />
        ) : (
          <p className="notice">
            This row is no longer on the current page. Close and refresh the
            transaction list.
          </p>
        )}
        {navigationDisabled && (
          <p className="subtle">
            Save or discard edits before closing or following a transfer.
          </p>
        )}
      </dialog>
    </>
  );
}
