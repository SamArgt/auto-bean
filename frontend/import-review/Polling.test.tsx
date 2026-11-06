// @vitest-environment jsdom
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Review } from "./src/Review";
import type { Bridge } from "./src/types";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});
test("polling pauses while hidden and does not overlap a slow read", async () => {
  vi.useFakeTimers();
  const hidden = vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  let finish: (value: unknown) => void = () => {};
  const response = new Promise((resolve) => {
    finish = resolve;
  });
  const call = vi.fn().mockReturnValue(response);
  render(
    <Review
      initialBinding={{ workspace: "/ledger", session_id: "session" }}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(6000);
  });
  expect(call).toHaveBeenCalledTimes(1);
  await act(async () => {
    finish({
      workspace: "/ledger",
      session_id: "session",
      etag: "0",
      groups: [],
      statements: [],
      price_runs: [],
    });
    await response;
  });
  expect(screen.getByText("0 statements · 0 outstanding inputs")).toBeTruthy();
  expect(screen.getByText("No imports available for review.")).toBeTruthy();
  expect(
    call.mock.calls.every(([name]) => name === "read_import_session"),
  ).toBe(true);
  hidden.mockReturnValue(true);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(6000);
  });
  expect(call).toHaveBeenCalledTimes(1);
  hidden.mockReturnValue(false);
  await act(async () => {
    document.dispatchEvent(new Event("visibilitychange"));
  });
  expect(call).toHaveBeenCalledTimes(2);
});
test("unchanged evidence reuses account counts, changed evidence and failed counts refresh", async () => {
  vi.useFakeTimers();
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  let etag = "1";
  let failCounts = false;
  const call = vi.fn(async (name: string) => {
    if (name === "read_import_session")
      return {
        workspace: "/ledger",
        session_id: "session",
        etag,
        groups: [],
        price_runs: [],
        statements: [
          {
            source_file: "a.csv",
            status: "categorize_blocked",
            needs_input: 1,
            error: null,
          },
        ],
      };
    if (name === "read_import_statement")
      return {
        source_file: "a.csv",
        etag,
        extraction_state: "complete",
        processing: { warnings: [] },
        statement_metadata: {
          accounts: [{ account_id: "checking", account_name: "Checking" }],
        },
      };
    if (failCounts) throw new Error("Temporary read failure");
    return { etag, total: 1, offset: 0, rows: [], received_inputs: [] };
  });
  render(
    <Review
      initialBinding={{ workspace: "/ledger", session_id: "session" }}
      bridge={{ call, continue: vi.fn() } as Bridge}
    />,
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  const countCalls = () =>
    call.mock.calls.filter(([name]) => name === "list_import_transactions")
      .length;
  expect(countCalls()).toBe(1);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(6000);
  });
  expect(countCalls()).toBe(1);
  etag = "2";
  failCounts = true;
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
  });
  expect(countCalls()).toBe(2);
  failCounts = false;
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
  });
  expect(countCalls()).toBe(3);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(2000);
  });
  expect(countCalls()).toBe(3);
});
test("hosts without continuation keep saved data available and disable sending", async () => {
  const continuation = vi.fn();
  const call = vi.fn().mockResolvedValue({
    workspace: "/ledger",
    session_id: "session",
    etag: "1",
    groups: [],
    statements: [],
    price_runs: [],
    review_batch: {
      pending_count: 1,
      pending_token: "1",
      token: "1",
      ready: true,
      blockers: [],
      subjects: ["a.csv"],
    },
  });
  render(
    <Review
      initialBinding={{ workspace: "/ledger", session_id: "session" }}
      bridge={{ call, continue: continuation, canContinue: false }}
    />,
  );
  const send = await screen.findByRole("button", {
    name: "Send saved changes",
  });
  expect((send as HTMLButtonElement).disabled).toBe(true);
  expect(
    screen.getByText(/Your changes are saved. Ask the agent/),
  ).toBeTruthy();
  expect(continuation).not.toHaveBeenCalled();
});
