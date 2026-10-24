// @vitest-environment jsdom
import { afterEach, beforeAll, expect, test, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { Review, TextEdit } from "./src/Review";
import { TransactionCard } from "./src/ReviewForms";
import type { Bridge, Detail, Overview, Transaction } from "./src/types";
afterEach(cleanup);
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});
const binding = { workspace: "/ledger", session_id: "session" };
const row: Transaction = {
  record_id: "r1",
  account_id: "checking",
  transaction_date: "2026-10-21",
  description: "Unknown transfer",
  amount: "-25",
  currency: "EUR",
  source_reference: "row:1",
  review: {
    state: "needs_input",
    disposition: "hold",
    rationale: "Confirm the destination.",
    postings: [],
    suggestions: ["Shared expense", "My savings"],
  },
};
const peer: Transaction = {
  ...row,
  record_id: "peer",
  account_id: "savings",
  description: "Transfer received",
  review: {
    state: "confirmed",
    disposition: "paired_transfer",
    rationale: "Matched transfer",
    postings: [],
    posting_owner: "r1",
    linked_records: [],
  },
};
const detail: Detail = {
  source_file: "a.csv",
  etag: "1",
  extraction_state: "complete",
  review_digest: "a".repeat(64),
  approval: null,
  validation: null,
  validation_current: null,
  processing: { warnings: [] },
  statement_metadata: {
    accounts: [
      {
        account_id: "checking",
        account_name: "Checking",
        review: {
          state: "confirmed",
          ledger_account: "Assets:Checking",
          rationale: "Matched",
        },
      },
    ],
  },
};
const overview: Overview = {
  ...binding,
  etag: "1",
  review_batch: {
    pending_count: 0,
    token: "1",
    pending_token: "1",
    ready: false,
    blockers: ["Review transfer"],
    subjects: [],
  },
  groups: [
    {
      group_id: "bank",
      name: "Bank",
      origin: "user",
      parsed_group: "group.json",
      current_status: "categorize_blocked",
      updated_at: null,
      source_files: ["a.csv", "b.csv"],
    },
  ],
  statements: ["a.csv", "b.csv"].map((source_file) => ({
    source_file,
    status: "categorize_blocked",
    updated_at: null,
    etag: "1",
    extraction_state: "complete",
    needs_input: 1,
    error: null,
  })),
  price_runs: [],
};
function bridgeFixture(linked = false) {
  const displayedRow = linked
    ? {
        ...row,
        review: {
          ...row.review!,
          linked_records: [
            { source_file: "b.csv", account_id: "savings", record_id: "peer" },
          ],
        },
      }
    : row;
  const call = vi.fn(async (name: string, args: Record<string, unknown>) => {
    if (name === "read_import_session") return overview;
    if (name === "read_import_statement")
      return args.source_file === "a.csv"
        ? detail
        : {
            ...detail,
            source_file: "b.csv",
            statement_metadata: {
              accounts: [{ account_id: "savings", account_name: "Savings" }],
            },
          };
    if (name === "list_import_transactions")
      return args.source_file === "a.csv"
        ? { etag: "1", offset: 0, total: 1, rows: [displayedRow] }
        : {
            etag: "1",
            offset: args.offset,
            total: 101,
            rows: args.offset === 100 ? [peer] : [],
          };
    if (name === "update_import_review")
      return {
        etag: "2",
        source_file: args.source_file,
        review_digest: detail.review_digest,
      };
    throw Error(name);
  });
  return { call, continue: vi.fn() } as Bridge & { call: typeof call };
}
test("suggestion choices preserve the original etag through a refresh", async () => {
  const save = vi.fn().mockResolvedValue(true);
  const { rerender } = render(
    <TextEdit
      label="Answer"
      value=""
      etag="1"
      choices={["My savings"]}
      disabled={false}
      onSave={save}
    />,
  );
  fireEvent.change(screen.getByLabelText("Answer choices"), {
    target: { value: "My savings" },
  });
  rerender(
    <TextEdit
      label="Answer"
      value=""
      etag="2"
      choices={["My savings"]}
      disabled={false}
      onSave={save}
    />,
  );
  fireEvent.click(screen.getByText("Save choice"));
  await waitFor(() => expect(save).toHaveBeenCalledWith("My savings", "1"));
});
test("account dialogs save real MCP answers and protect drafts from navigation", async () => {
  const bridge = bridgeFixture();
  render(<Review initialBinding={binding} bridge={bridge} />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Checking.*a.csv/ }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Unknown transfer" }),
  );
  fireEvent.change(screen.getByLabelText("Transaction answer choices"), {
    target: { value: "My savings" },
  });
  expect(
    (
      screen.getByRole("button", {
        name: "Close transaction",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  // The modal makes sidebar controls inaccessible; the disabled DOM button also prevents a lost draft.
  expect((screen.getByText("Price") as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByText("Refresh"));
  expect(
    (screen.getByLabelText("Transaction answer") as HTMLInputElement).value,
  ).toBe("My savings");
  fireEvent.click(screen.getByText("Save choice"));
  await waitFor(() =>
    expect(bridge.call).toHaveBeenCalledWith("update_import_review", {
      ...binding,
      source_file: "a.csv",
      update: {
        kind: "answer",
        subject_kind: "transaction",
        subject_id: "r1",
        value: "My savings",
        expected_etag: "1",
      },
    }),
  );
  expect(bridge.continue).not.toHaveBeenCalled();
  await waitFor(() =>
    expect(
      (
        screen.getByRole("button", {
          name: "Close transaction",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false),
  );
  fireEvent.click(screen.getByRole("button", { name: "Close transaction" }));
  fireEvent.click(screen.getByRole("button", { name: "Price", exact: true }));
  expect(
    await screen.findByText("Price results are not available yet."),
  ).toBeTruthy();
});
test("a linked transfer opens its exact peer beyond the first page", async () => {
  const bridge = bridgeFixture(true);
  render(<Review initialBinding={binding} bridge={bridge} />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Checking.*a.csv/ }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Unknown transfer" }),
  );
  fireEvent.click(screen.getByText("Evidence & rationale"));
  fireEvent.click(screen.getByRole("button", { name: /Follow transfer/ }));
  await screen.findByRole("heading", { name: "Transfer received" });
  expect(bridge.call).toHaveBeenCalledWith(
    "list_import_transactions",
    expect.objectContaining({
      source_file: "b.csv",
      account_id: "savings",
      offset: 100,
      limit: 100,
    }),
  );
  expect(screen.queryByText("Correct postings")).toBeNull();
  expect(screen.getByText(/Posting owner: r1/)).toBeTruthy();
});
test("posting corrections keep split amounts, fees, unit costs and prices", async () => {
  const save = vi.fn().mockResolvedValue(true);
  render(
    <TransactionCard
      row={{
        ...row,
        review: {
          ...row.review!,
          postings: [
            {
              account: "Assets:Broker",
              amount: "2",
              currency: "FUND",
              cost: "{12 EUR}",
              price: "@ 13 EUR",
            },
          ],
        },
      }}
      etag="1"
      disabled={false}
      onSave={save}
      onAnswer={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByText("Correct postings"));
  fireEvent.click(screen.getByText("Add split posting"));
  const split = screen.getByRole("group", { name: "Posting 2" });
  fireEvent.change(within(split).getByLabelText("account"), {
    target: { value: "Expenses:Fees" },
  });
  fireEvent.change(within(split).getByLabelText("amount"), {
    target: { value: "1" },
  });
  fireEvent.click(screen.getByText("Save correction"));
  await waitFor(() =>
    expect(save).toHaveBeenCalledWith(
      [
        {
          account: "Assets:Broker",
          amount: "2",
          currency: "FUND",
          cost: "{12 EUR}",
          price: "@ 13 EUR",
        },
        { account: "Expenses:Fees", amount: "1", currency: "EUR" },
      ],
      "1",
    ),
  );
});

test("polling cannot discard an open draft when its row leaves the page", async () => {
  const { TransactionTable } = await import("./src/TransactionTable");
  const props = {
    source: "a.csv",
    disabled: false,
    navigationDisabled: false,
    onLink: vi.fn(),
    onAnswer: vi.fn(),
    onSave: vi.fn(),
  };
  const { rerender } = render(
    <TransactionTable
      {...props}
      page={{ etag: "1", total: 1, offset: 0, rows: [row] }}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Unknown transfer" }));
  fireEvent.change(screen.getByLabelText("Transaction answer choices"), {
    target: { value: "__custom" },
  });
  fireEvent.change(screen.getByLabelText("Transaction answer"), {
    target: { value: "My unsaved correction" },
  });
  rerender(
    <TransactionTable
      {...props}
      page={{ etag: "2", total: 0, offset: 0, rows: [] }}
    />,
  );
  expect(
    (screen.getByLabelText("Transaction answer") as HTMLInputElement).value,
  ).toBe("My unsaved correction");
  expect(
    screen.getByText(/This transaction left the current page/),
  ).toBeTruthy();
  expect((screen.getByText("Save answer") as HTMLButtonElement).disabled).toBe(
    true,
  );
});
