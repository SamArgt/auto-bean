// @vitest-environment jsdom
import { afterEach, expect, test, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { Review, TextEdit } from "./src/Review";
import type { Bridge } from "./src/types";
afterEach(cleanup);
test("refresh preserves an unsaved edit and reports its original etag", async () => {
  const save = vi.fn().mockResolvedValue(true);
  const { rerender } = render(
    <TextEdit
      label="Mapping"
      value="Assets:Old"
      etag={"1"}
      disabled={false}
      onSave={save}
    />,
  );
  fireEvent.change(screen.getByLabelText("Mapping"), {
    target: { value: "Assets:Chosen" },
  });
  rerender(
    <TextEdit
      label="Mapping"
      value="Assets:New"
      etag={"2"}
      disabled={false}
      onSave={save}
    />,
  );
  expect((screen.getByLabelText("Mapping") as HTMLInputElement).value).toBe(
    "Assets:Chosen",
  );
  expect(screen.getByRole("status").textContent).toContain(
    "changed while you were editing",
  );
  fireEvent.click(screen.getByText("Save correction"));
  await waitFor(() => expect(save).toHaveBeenCalledWith("Assets:Chosen", "1"));
});
test("saves stay silent until explicit batch send; notification retry does not save again", async () => {
  let changed=false;
  const batch={pending_count:1,pending_token:"pending",token:"snapshot",blockers:[],ready:true,subjects:["statements/raw/a.csv"]};
  const saved = {
    source_file: "statements/raw/a.csv",
    etag: "4",
    review_digest: "a".repeat(64),
  };
  const call = vi.fn(async (name: string, args: Record<string, unknown>) => {
    if (name === "read_import_session")
      return {
        workspace: "/ledger",
        review_batch: {...batch, ready:changed, pending_count:changed?1:0},
        session_id: "session",
        etag: "0",
        groups: [
          {
            group_id: "a",
            parsed_group: "statements/parsed/group.json",
            current_status: "raw_ready",
            updated_at: null,
            name: "Checking",
            origin: "agent",
            source_files: ["statements/raw/a.csv"],
          },
        ],
        statements: [
          {
            source_file: "statements/raw/a.csv",
            status: "account_review",
            needs_input: 1,
          },
        ],
        price_runs: [],
      };
    if (name === "read_import_statement")
      return {
        source_file: "statements/raw/a.csv",
        etag: "3",
        extraction_state: "complete",
        review_digest: "a".repeat(64),
        approval: null,
        validation: null,
        statement_metadata: { accounts: [] },
        processing: {
          warnings: [],
          needs_input: true,
          suggestions: ["Identify the statement"],
        },
      };
    if (name === "list_import_transactions") {
      expect(args).not.toHaveProperty("account_id");
      return { etag: "3", total: 0, offset: 0, rows: [] };
    }
    if (name === "update_import_review") {changed=true;return saved;}
    if (name === "prepare_import_review_batch") return batch;
    if (name === "acknowledge_import_review_batch") {changed=false;return {...batch,ready:false,pending_count:0};}
    throw Error(name);
  });
  const resume = vi
    .fn()
    .mockRejectedValueOnce(Error("host offline"))
    .mockResolvedValue(undefined);
  render(
    <Review
      initialBinding={{ workspace: "/ledger", session_id: "session" }}
      bridge={{ call, continue: resume } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  fireEvent.change(await screen.findByLabelText("Processing answer"), {
    target: { value: "Checking" },
  });
  fireEvent.click(screen.getByText("Save answer"));
  await waitFor(() => expect((screen.getByText("Send saved changes") as HTMLButtonElement).disabled).toBe(false));
  expect(resume).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Send saved changes"));
  await screen.findByText(/Send failed/);
  fireEvent.click(screen.getByText("Send saved changes"));
  await waitFor(() => expect(resume).toHaveBeenCalledTimes(2));
  expect(resume.mock.calls).toEqual([
    ["session", ["statements/raw/a.csv"]],
    ["session", ["statements/raw/a.csv"]],
  ]);
  expect(
    call.mock.calls.filter(([name]) => name === "update_import_review"),
  ).toHaveLength(1);
  expect(
    call.mock.calls.find(([name]) => name === "update_import_review")?.[1]
      .update,
  ).toMatchObject({
    kind: "answer",
    subject_kind: "statement",
    subject_id: "statement",
    expected_etag: "3",
  });
  const transactionCalls = call.mock.calls.filter(
    ([name]) => name === "list_import_transactions",
  );
  expect(transactionCalls.length).toBeGreaterThan(0);
  for (const [, args] of transactionCalls)
    expect(args).not.toHaveProperty("account_id");
});

const binding = { workspace: "/ledger", session_id: "session" };
const summary = {
  ...binding,
  etag: "0",
  groups: [
    {
      group_id: "a",
      parsed_group: "statements/parsed/group.json",
      current_status: "raw_ready",
      updated_at: null,
      name: "Checking",
      origin: "agent",
      source_files: ["statements/raw/a.csv"],
    },
  ],
  statements: [
    {
      source_file: "statements/raw/a.csv",
      status: "account_review",
      needs_input: 1,
    },
  ],
  price_runs: [],
};
const details = {
  source_file: "statements/raw/a.csv",
  etag: "3",
  extraction_state: "complete",
  review_digest: "a".repeat(64),
  approval: null,
  validation: null,
  statement_metadata: { accounts: [] },
  processing: {
    warnings: [],
    needs_input: true,
    suggestions: ["Identify the statement"],
  },
};
function fixtureCall(name: string) {
  if (name === "read_import_session") return summary;
  if (name === "read_import_statement") return details;
  if (name === "list_import_transactions")
    return { etag: "3", total: 0, offset: 0, rows: [] };
  throw Error(name);
}

test("an uncertain save is retried against the original etag without continuation", async () => {
  const actions: Record<string, unknown>[] = [];
  const call = vi.fn(async (name: string, args: Record<string, unknown>) => {
    if (name === "update_import_review") {
      actions.push(args.update as Record<string, unknown>);
      if (actions.length === 1) throw Error("response disconnected");
      return {
        source_file: "statements/raw/a.csv",
        etag: "4",
        review_digest: "a".repeat(64),
      };
    }
    return fixtureCall(name);
  });
  const resume = vi.fn().mockResolvedValue(undefined);
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: resume } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  fireEvent.change(await screen.findByLabelText("Processing answer"), {
    target: { value: "Checking" },
  });
  fireEvent.click(screen.getByText("Save answer"));
  await screen.findByText("Error: response disconnected");
  expect(resume).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Save answer"));
  await waitFor(() => expect(actions).toHaveLength(2));
  expect(resume).not.toHaveBeenCalled();
  expect(actions).toHaveLength(2);
  expect(actions[0]).toEqual(actions[1]);
  expect(actions[0]).not.toHaveProperty("action_id");
  expect(actions[0]).toHaveProperty("expected_etag", "3");
});

test("pagination is bounded and needs-input filtering resets the offset", async () => {
  const call = vi.fn(async (name: string, args: Record<string, unknown>) => {
    if (name === "list_import_transactions")
      return { etag: "3", total: 201, offset: args.offset, rows: [] };
    return fixtureCall(name);
  });
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  fireEvent.click(await screen.findByText("Next"));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith(
      "list_import_transactions",
      expect.objectContaining({ offset: 100, limit: 100 }),
    ),
  );
  fireEvent.click(screen.getByLabelText("Needs input"));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith(
      "list_import_transactions",
      expect.objectContaining({ offset: 0, limit: 100, needs_input: true }),
    ),
  );
});

test("read errors retain drafts and pause dependent corrections", async () => {
  let fail = false;
  const call = vi.fn(async (name: string) => {
    if (fail && name === "read_import_statement")
      throw Error("invalid artifact");
    return fixtureCall(name);
  });
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  fireEvent.change(await screen.findByLabelText("Processing answer"), {
    target: { value: "My unsaved answer" },
  });
  fail = true;
  fireEvent.click(screen.getByText("Refresh"));
  await screen.findByText(/Refresh failed/);
  expect(
    (screen.getByLabelText("Processing answer") as HTMLInputElement).value,
  ).toBe("My unsaved answer");
  expect((screen.getByText("Save answer") as HTMLButtonElement).disabled).toBe(
    true,
  );
  fail = false;
  fireEvent.click(screen.getByText("Refresh"));
  await waitFor(() =>
    expect(
      (screen.getByText("Save answer") as HTMLButtonElement).disabled,
    ).toBe(false),
  );
  expect(
    (screen.getByLabelText("Processing answer") as HTMLInputElement).value,
  ).toBe("My unsaved answer");
});

test("a new host session cannot retain the previous session statement", async () => {
  const call = vi.fn(async (name: string, args: Record<string, unknown>) =>
    name === "read_import_session"
      ? { ...summary, session_id: args.session_id }
      : fixtureCall(name),
  );
  const bridge = { call, continue: vi.fn() } as Bridge;
  const { rerender } = render(
    <Review initialBinding={binding} bridge={bridge} />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  await screen.findByLabelText("Processing answer");
  rerender(
    <Review
      initialBinding={{ ...binding, session_id: "different" }}
      bridge={bridge}
    />,
  );
  await screen.findByText(/Session different/);
  expect(screen.queryByLabelText("Processing answer")).toBeNull();
});

test("a mistyped manual binding can be corrected in the panel", async () => {
  const call = vi.fn().mockRejectedValue(Error("unknown session"));
  render(
    <Review
      initialBinding={null}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  fireEvent.change(screen.getByLabelText("Ledger workspace"), {
    target: { value: "/ledger" },
  });
  fireEvent.change(screen.getByLabelText("Session ID"), {
    target: { value: "typo" },
  });
  fireEvent.click(screen.getByText("Open session"));
  await screen.findByText(/Refresh failed/);
  fireEvent.click(screen.getByText("Change session"));
  expect((screen.getByLabelText("Session ID") as HTMLInputElement).value).toBe(
    "typo",
  );
});

test("an unchanged proposed mapping can be explicitly confirmed against the latest etag", async () => {
  const save = vi.fn().mockResolvedValue(true);
  const { rerender } = render(
    <TextEdit
      label="Ledger mapping"
      value="Assets:Checking"
      etag={"1"}
      allowConfirm
      disabled={false}
      onSave={save}
    />,
  );
  rerender(
    <TextEdit
      label="Ledger mapping"
      value="Assets:Checking"
      etag={"2"}
      allowConfirm
      disabled={false}
      onSave={save}
    />,
  );
  fireEvent.click(screen.getByText("Confirm mapping"));
  await waitFor(() =>
    expect(save).toHaveBeenCalledWith("Assets:Checking", "2"),
  );
});

test("completed statements disable mapping confirmation and corrections", async () => {
  const call = vi.fn(async (name: string) => {
    if (name === "read_import_session")
      return {
        ...summary,
        statements: [{ ...summary.statements[0], status: "done" }],
      };
    if (name === "read_import_statement")
      return {
        ...details,
        statement_metadata: {
          accounts: [
            {
              account_id: "checking",
              account_name: "Checking",
              review: {
                state: "needs_input",
                ledger_account: "Assets:Checking",
                rationale: "Proposed",
              },
            },
          ],
        },
      };
    return fixtureCall(name);
  });
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  const button = await screen.findByText("Confirm mapping");
  expect((button as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Processing answer"), {
    target: { value: "An edit" },
  });
  expect(
    screen
      .getAllByText("Save answer")
      .every((button) => (button as HTMLButtonElement).disabled),
  ).toBe(true);
  expect(screen.getByText(/Request explicit rework/)).toBeTruthy();
});

test("approval binds the currently displayed statement etag and digest", async () => {
  const call = vi.fn(async (name: string, args: Record<string, unknown>) => {
    if (name === "read_import_session")
      return {
        ...summary,
        statements: [
          { ...summary.statements[0], status: "final_review", needs_input: 0 },
        ],
      };
    if (name === "read_import_statement")
      return { ...details, processing: { warnings: [] } };
    if (name === "update_import_review")
      return {
        source_file: args.source_file,
        etag: "4",
        review_digest: details.review_digest,
      };
    return fixtureCall(name);
  });
  const resume = vi.fn().mockResolvedValue(undefined);
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: resume } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  fireEvent.click(await screen.findByText("Approve reviewed transactions"));
  await screen.findByText(/Saved to JSON/);
  expect(resume).not.toHaveBeenCalled();
  expect(call).toHaveBeenCalledWith("update_import_review", {
    ...binding,
    source_file: "statements/raw/a.csv",
    update: {
      kind: "approve",
      subject_id: "statement",
      expected_etag: "3",
      review_digest: details.review_digest,
    },
  });
});

test("unresolved input and stale reads disable approval", async () => {
  let ready = true;
  const call = vi.fn(async (name: string) => {
    if (name === "read_import_session")
      return {
        ...summary,
        statements: [
          {
            ...summary.statements[0],
            status: ready ? "final_review" : "categorize_blocked",
            needs_input: ready ? 0 : 1,
          },
        ],
      };
    return fixtureCall(name);
  });
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  expect(
    (
      (await screen.findByText(
        "Approve reviewed transactions",
      )) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
  ready = false;
  fireEvent.click(screen.getByText("Refresh"));
  await waitFor(() =>
    expect(
      (screen.getByText("Approve reviewed transactions") as HTMLButtonElement)
        .disabled,
    ).toBe(true),
  );
});

test("unsaved inline edits block approval until discarded", async () => {
  const call = vi.fn(async (name: string) => {
    if (name === "read_import_session")
      return {
        ...summary,
        statements: [
          { ...summary.statements[0], status: "final_review", needs_input: 0 },
        ],
      };
    if (name === "read_import_statement")
      return {
        ...details,
        processing: { warnings: [] },
        statement_metadata: {
          accounts: [
            {
              account_id: "checking",
              account_name: "Checking",
              review: {
                state: "confirmed",
                ledger_account: "Assets:Checking",
                rationale: "Mapped",
              },
            },
          ],
        },
      };
    return fixtureCall(name);
  });
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  const approve = (await screen.findByText(
    "Approve reviewed transactions",
  )) as HTMLButtonElement;
  expect(approve.disabled).toBe(false);
  fireEvent.change(screen.getByLabelText("Ledger mapping"), {
    target: { value: "Assets:Savings" },
  });
  await waitFor(() => expect(approve.disabled).toBe(true));
  fireEvent.click(screen.getByText("Discard edit"));
  await waitFor(() => expect(approve.disabled).toBe(false));
});

test("approval waits for matching statement and transaction etags", async () => {
  let pageEtag = "2";
  const call = vi.fn(async (name: string) => {
    if (name === "read_import_session")
      return {
        ...summary,
        statements: [
          { ...summary.statements[0], status: "final_review", needs_input: 0 },
        ],
      };
    if (name === "list_import_transactions")
      return { etag: pageEtag, total: 0, offset: 0, rows: [] };
    return fixtureCall(name);
  });
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("a.csv"));
  const approve = (await screen.findByText(
    "Approve reviewed transactions",
  )) as HTMLButtonElement;
  expect(approve.disabled).toBe(true);
  expect(screen.getByText(/different snapshots/)).toBeTruthy();
  pageEtag = "3";
  fireEvent.click(screen.getByText("Refresh"));
  await waitFor(() => expect(approve.disabled).toBe(false));
});

test("price approval saves the current run before continuing without a statement action", async () => {
  const digest = "b".repeat(64);
  const call = vi.fn(async (name: string) => {
    if (name === "read_import_session")
      return {
        ...summary,
        etag: "7",
        price_runs: [
          {
            run_id: "prices",
            review_digest: digest,
            requested_date: "2026-01-31",
            state: "complete",
            required_commodities: ["STOCK"],
            coverage: ["STOCK"],
            preflight: "passed",
            preflight_job_count: 1,
            execution: {
              state: "complete",
              exit_code: 0,
              duration_seconds: 1,
              stderr_summary: "",
            },
            jobs: [
              {
                commodity: "STOCK",
                source: "fixture",
                requested_date: "2026-01-31",
                quote_date: "2026-01-31",
                outcome: "emitted",
                directive: "2026-01-31 price STOCK 20 EUR",
              },
            ],
            detail: "Synthetic quote",
          },
        ],
      };
    if (name === "approve_import_prices")
      return { run_id: "prices", etag: "8", review_digest: digest };
    return fixtureCall(name);
  });
  const resume = vi.fn().mockResolvedValue(undefined);
  render(
    <Review
      initialBinding={binding}
      bridge={{ call, continue: resume } as Bridge}
    />,
  );
  fireEvent.click(await screen.findByText("Approve price directives"));
  await screen.findByText(/Price approval saved to JSON/);
  expect(resume).not.toHaveBeenCalled();
  expect(call).toHaveBeenCalledWith("approve_import_prices", {
    ...binding,
    run_id: "prices",
    expected_etag: "7",
    review_digest: digest,
  });
  expect(
    call.mock.calls.some(([name]) => name === "update_import_review"),
  ).toBe(false);
});

test("batch send is blocked by required inputs and unsaved drafts", async () => {
  let ready=false;
  const batch={pending_count:1,pending_token:"pending",token:"snapshot",blockers:["Other account needs input"],ready:false,subjects:["a.csv"]};
  const call=vi.fn(async(name:string)=>name==='read_import_session'?{...summary,review_batch:{...batch,ready,blockers:ready?[]:batch.blockers}}:fixtureCall(name));
  const resume=vi.fn();
  render(<Review initialBinding={binding} bridge={{call,continue:resume} as Bridge}/>);
  const send=await screen.findByText('Send saved changes') as HTMLButtonElement;
  expect(send.disabled).toBe(true);
  ready=true;fireEvent.click(screen.getByText('Refresh'));
  await waitFor(()=>expect(send.disabled).toBe(false));
  fireEvent.click(screen.getByText('a.csv'));
  fireEvent.change(await screen.findByLabelText('Processing answer'),{target:{value:'Unsaved answer'}});
  await waitFor(()=>expect(send.disabled).toBe(true));
  expect(resume).not.toHaveBeenCalled();
});

test("acknowledgement retry does not notify the agent twice", async () => {
  const batch={pending_count:1,pending_token:"pending",token:"snapshot",blockers:[],ready:true,subjects:["a.csv"]};
  let attempts=0;
  const call=vi.fn(async(name:string)=>{
    if(name==='read_import_session')return {...summary,review_batch:batch};
    if(name==='prepare_import_review_batch')return batch;
    if(name==='acknowledge_import_review_batch'){if(++attempts===1)throw Error('Temporary acknowledgement failure');return batch;}
    return fixtureCall(name);
  });
  const resume=vi.fn().mockResolvedValue(undefined);
  render(<Review initialBinding={binding} bridge={{call,continue:resume} as Bridge}/>);
  fireEvent.click(await screen.findByText('Send saved changes'));
  const retry=await screen.findByText('Finish sent batch') as HTMLButtonElement;
  await waitFor(()=>expect(retry.disabled).toBe(false));
  fireEvent.click(retry);
  await screen.findByText(/Saved changes sent/);
  expect(attempts).toBe(2);expect(resume).toHaveBeenCalledTimes(1);
});
