// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { StatementValidation, SessionPrices } from "./src/ReviewPanels";
import { TransactionCard } from "./src/ReviewForms";
import type { Detail, Overview, Transaction } from "./src/types";
afterEach(cleanup);
const detail: Detail = {
  source_file: "statements/raw/a.csv",
  etag: "3",
  review_digest: "a".repeat(64),
  extraction_state: "complete",
  statement_metadata: { accounts: [] },
  processing: { warnings: [] },
  approval: null,
  validation: null,
  validation_current: null,
};
test("approval shows the reviewed state and validation distinguishes stale results", () => {
  const decide = vi.fn().mockResolvedValue(true);
  const { rerender } = render(
    <StatementValidation
      detail={detail}
      canApprove
      disabled={false}
      onDecision={decide}
    />,
  );
  fireEvent.click(screen.getByText("Approve reviewed transactions"));
  expect(decide).toHaveBeenCalledWith("approve");
  rerender(
    <StatementValidation
      detail={{
        ...detail,
        review_digest: "b".repeat(64),
        approval: {
          digest: "a".repeat(64),
          approved_at: "2026-10-21T10:00:00Z",
          origin: "panel",
        },
        validation: {
          stage: "written",
          state: "passed",
          checked_at: "2026-10-21T10:00:00Z",
          digest: "a".repeat(64),
          ledger_hashes: {},
          records_checked: 1,
          balances: [],
          errors: [],
        },
      }}
      canApprove={false}
      disabled={false}
      onDecision={decide}
    />,
  );
  expect(screen.getByText(/Stale result/)).toBeTruthy();
  expect(
    (screen.getByText("Approve reviewed transactions") as HTMLButtonElement)
      .disabled,
  ).toBe(true);
});
test("price execution and zero-job results are explicit", () => {
  const overview: Overview = {
    workspace: "/ledger",
    session_id: "s1",
    etag: "1",
    groups: [],
    statements: [],
    price_runs: [
      {
        run_id: "p1",
        review_digest: "a".repeat(64),
        validation_current: null,
        requested_date: "2026-10-21",
        state: "no_op",
        required_commodities: [],
        coverage: [],
        preflight: "passed",
        preflight_job_count: 0,
        execution: {
          state: "complete",
          exit_code: 0,
          duration_seconds: 0,
          stderr_summary: "",
        },
        detail: "EUR-only session",
        jobs: [],
      },
    ],
  };
  render(
    <SessionPrices overview={overview} disabled={false} onApprove={vi.fn()} />,
  );
  expect(screen.getByText("Zero price jobs.")).toBeTruthy();
  expect(screen.getByText(/Execution: complete/).textContent).toContain(
    "Exit 0",
  );
  expect(screen.getByText(/Preflight:/).textContent).toContain("(0 jobs)");
});

test("duplicate transaction evidence identifies the verified canonical entry", () => {
  const row: Transaction = {
    record_id: "r1",
    account_id: "a1",
    transaction_date: "2026-10-21",
    description: "Existing grocery payment",
    amount: "-25",
    currency: "EUR",
    source_reference: "Row 1",
    review: {
      state: "confirmed",
      postings: [],
      rationale: "Matches an existing ledger entry",
      findings: [],
      disposition: "existing_duplicate",
      linked_records: [],
      existing_transaction: {
        path: "beancount/2026.beancount",
        line: 42,
      },
    },
  };
  render(
    <TransactionCard
      row={row}
      etag={"1"}
      disabled={false}
      onSave={vi.fn()}
      onAnswer={vi.fn()}
    />,
  );
  expect(
    screen.getByText(/Existing ledger transaction:/).textContent,
  ).toContain("beancount/2026.beancount · Line 42");
});

test("transaction input is inline and an unreviewed row stays pending", () => {
  const row: Transaction = {
    record_id: "r2",
    account_id: "a1",
    transaction_date: "2026-10-21",
    description: "Transfer",
    amount: "-25",
    currency: "EUR",
    source_reference: "Row 2",
  };
  const answer = vi.fn().mockResolvedValue(true);
  const { rerender } = render(
    <TransactionCard
      row={row}
      etag={"2"}
      disabled={false}
      onSave={vi.fn()}
      onAnswer={answer}
    />,
  );
  expect(screen.getByText("Categorization pending")).toBeTruthy();
  expect(screen.queryByText(/Needs input/)).toBeNull();
  rerender(
    <TransactionCard
      row={{
        ...row,
        review: {
          state: "needs_input",
          disposition: "hold",
          postings: [],
          rationale: "Destination unknown",
          suggestions: ["Confirm the destination account"],
        },
      }}
      etag={"3"}
      disabled={false}
      onSave={vi.fn()}
      onAnswer={answer}
    />,
  );
  expect(screen.getByText("Confirm the destination account")).toBeTruthy();
  expect(screen.getByText(/Needs input/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Transaction answer"), {
    target: { value: "My savings account" },
  });
  fireEvent.click(screen.getByText("Save answer"));
  expect(answer).toHaveBeenCalledWith("My savings account", "3");
});

test("review readiness never claims ledger writes or absence of conversational approval", () => {
  render(
    <StatementValidation
      detail={{
        ...detail,
        validation_current: true,
        validation: {
          stage: "review",
          state: "passed",
          checked_at: "2026-10-21T10:00:00Z",
          digest: detail.review_digest,
          ledger_hashes: {},
          records_checked: 1,
          balances: [],
          errors: [],
        },
      }}
      canApprove
      disabled={false}
      onDecision={vi.fn()}
    />,
  );
  expect(screen.getByText("Review readiness validation")).toBeTruthy();
  expect(
    screen.getByText(/does not confirm that transactions have been written/),
  ).toBeTruthy();
  expect(
    screen.getByText(
      /No panel confirmation. Approval can also be given in conversation/,
    ),
  ).toBeTruthy();
  expect(screen.queryByText("Ledger write validation")).toBeNull();
});

test("session shows persisted multi-statement groups", () => {
  render(
    <SessionPrices
      overview={{
        workspace: "/ledger",
        session_id: "groups",
        etag: "1",
        statements: [],
        price_runs: [],
        groups: [
          {
            group_id: "january",
            parsed_group: "statements/parsed/group.json",
            current_status: "raw_ready",
            updated_at: null,
            name: "January accounts",
            origin: "user",
            source_files: [
              "statements/raw/checking.csv",
              "statements/raw/savings.pdf",
            ],
          },
        ],
      }}
      disabled={false}
      onApprove={vi.fn()}
    />,
  );
  expect(screen.getByText("January accounts")).toBeTruthy();
  expect(screen.getByText("User-defined")).toBeTruthy();
  expect(screen.getByText("statements/raw/checking.csv")).toBeTruthy();
  expect(screen.getByText("statements/raw/savings.pdf")).toBeTruthy();
});
