// @vitest-environment jsdom
import { afterEach, expect, test, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { ReviewExport } from "./src/ReviewExport";
import type { Bridge } from "./src/types";
afterEach(cleanup);
const binding = { workspace: "/ledger", session_id: "selected-session" };
const exported = {
  path: "/ledger/.auto-bean/exports/review.html",
  filename: "review.html",
  exported_at: "2026-10-21T12:00:00Z",
  sha256: "a".repeat(64),
};
test("exports the selected session and opens the durable local file without a continuation", async () => {
  const call = vi.fn().mockResolvedValue(exported),
    openFile = vi.fn().mockResolvedValue(undefined),
    resume = vi.fn();
  render(
    <ReviewExport
      binding={binding}
      bridge={{ call, openFile, continue: resume } as Bridge}
    />,
  );
  fireEvent.click(screen.getByText("Export HTML"));
  fireEvent.click(await screen.findByText("Open saved HTML"));
  await waitFor(() => expect(openFile).toHaveBeenCalledWith(exported.path));
  expect(call).toHaveBeenCalledExactlyOnceWith("export_import_review", binding);
  expect(resume).not.toHaveBeenCalled();
  expect(screen.getByText(exported.path)).toBeTruthy();
});
test("keeps the saved path when native opening fails and retries opening without exporting again", async () => {
  const call = vi.fn().mockResolvedValue(exported),
    openFile = vi
      .fn()
      .mockRejectedValueOnce(Error("viewer unavailable"))
      .mockResolvedValue(undefined);
  render(
    <ReviewExport
      binding={binding}
      bridge={{ call, openFile, continue: vi.fn() } as Bridge}
    />,
  );
  fireEvent.click(screen.getByText("Export HTML"));
  fireEvent.click(await screen.findByText("Open saved HTML"));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "file is saved",
  );
  fireEvent.click(screen.getByText("Open saved HTML"));
  await waitFor(() => expect(openFile).toHaveBeenCalledTimes(2));
  expect(call).toHaveBeenCalledTimes(1);
});
test("reports invalid-session export failure without claiming a file was saved", async () => {
  render(
    <ReviewExport
      binding={binding}
      bridge={
        {
          call: vi.fn().mockRejectedValue(Error("Invalid artifact")),
          continue: vi.fn(),
        } as Bridge
      }
    />,
  );
  fireEvent.click(screen.getByText("Export HTML"));
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Invalid artifact",
  );
  expect(screen.queryByText("Open saved HTML")).toBeNull();
});
