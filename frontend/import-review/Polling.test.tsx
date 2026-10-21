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
      statements: [],
      price_runs: [],
    });
    await response;
  });
  expect(screen.getByText("0 statements · 0 outstanding inputs")).toBeTruthy();
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
