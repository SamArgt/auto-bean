// Adapt synthetic demo storage to the plugin bridge. All visible review controls
// come from frontend/import-review/src/Review.tsx.
import { buildModel, questions, reviewAvailable } from "./model.mjs";
export function demoModel(state) {
  const model = buildModel(state.session, state.status, state.documents);
  for (const s of model.statements) {
    const prefix = s.doc.source_file + "#";
    for (const [key, value] of Object.entries(state.batch.answers)) {
      if (key.startsWith(prefix))
        s.answers.set(key.slice(prefix.length), value);
    }
    s.approved = state.batch.approvals.includes(s.doc.source_file);
  }
  return model;
}
const inputKey = (key) =>
  key === "source" ? "statement" : key.replace(/^row:/, "transaction:");
const needs = (r) =>
  r.review?.state === "needs_input" || r.review?.disposition === "hold";
export function demoResult(state, name, args = {}) {
  const model = demoModel(state),
    token = state.batch.token;
  const received = (s) => [...s.answers.keys()].map(inputKey);
  const detail = (s) => ({
    ...s.doc,
    processing: s.doc.review.processing,
    received_inputs: received(s),
    etag: token,
    review_digest: s.doc.review.approval?.digest ?? token,
    approval: s.doc.review.approval ?? null,
    validation: s.doc.review.validation ?? null,
    validation_current: s.doc.review.validation?.state === "passed",
  });
  const blockers = model.statements.flatMap((s) => [
    ...questions(s).map((q) => s.doc.source_file + ": " + q.text),
    ...(s.status === "final_review" && reviewAvailable(s) && !s.approved
      ? [s.doc.source_file + ": statement approval"]
      : []),
  ]);
  blockers.push(
    ...model.prices
      .filter(
        (p) => p.jobs?.some((j) => j.outcome === "emitted") && !p.approval,
      )
      .map((p) => "Price approval: " + p.run_id),
  );
  const batch = {
    pending_count: Object.keys(state.batch.pending).length,
    pending_token: token,
    token,
    blockers,
    ready: Object.keys(state.batch.pending).length > 0 && !blockers.length,
    subjects: Object.keys(state.batch.pending),
  };
  if (name === "read_import_session")
    return {
      workspace: state.directory,
      session_id: state.session.session_id,
      etag: token,
      review_batch: batch,
      groups: model.groups.map((g) => ({
        ...g,
        current_status: g.status,
        updated_at: null,
      })),
      statements: model.statements.map((s) => ({
        source_file: s.doc.source_file,
        status: s.status,
        updated_at: null,
        etag: token,
        extraction_state: s.doc.extraction_state,
        needs_input: questions(s).length,
        error: null,
      })),
      price_runs: model.prices.map((p) => ({
        ...p,
        review_digest: p.approval?.digest ?? token,
        validation_current: p.validation?.state === "passed",
      })),
    };
  if (name === "prepare_import_review_batch") {
    if (args.token !== token || !batch.ready)
      throw Error("Review inputs changed or remain unanswered.");
    return batch;
  }
  if (name === "search_ledger_accounts")
    return {
      accounts: [
        ...new Set(
          model.accounts.map((a) => a.review?.ledger_account).filter(Boolean),
        ),
      ].filter((a) =>
        a.toLowerCase().includes(String(args.query).toLowerCase()),
      ),
    };
  const s = model.statements.find(
    (s) => s.doc.source_file === args.source_file,
  );
  if (!s) throw Error("Unknown demo statement");
  if (name === "read_import_statement") return detail(s);
  if (name === "list_import_transactions") {
    const rows = s.doc.extracted_records.filter(
      (r) =>
        (!args.account_id || r.account_id === args.account_id) &&
        (!args.needs_input || needs(r)),
    );
    const offset = args.offset ?? 0;
    return {
      etag: token,
      total: rows.length,
      offset,
      received_inputs: rows
        .filter((r) => s.answers.has("row:" + r.record_id))
        .map((r) => r.record_id),
      rows: rows.slice(offset, offset + (args.limit ?? 100)),
    };
  }
  throw Error("Unsupported demo operation: " + name);
}
export function createDemoBridge(stage, onState, options = {}) {
  async function request(path, body) {
    const response = await fetch(
      body ? path : path + "?stage=" + stage,
      body
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stage, ...body }),
          }
        : undefined,
    );
    const state = await response.json();
    if (!response.ok) throw Error(state.error ?? "Demo request failed");
    onState(state);
    return state;
  }
  return {
    reset: () => request("/api/reset", {}),
    async call(name, args) {
      if (
        [
          "update_import_review",
          "approve_import_prices",
          "acknowledge_import_review_batch",
        ].includes(name)
      ) {
        await new Promise((resolve) =>
          setTimeout(resolve, options.delay?.() ?? 900),
        );
        if (options.fail?.())
          throw Error(
            "Simulated save failure. Try again with failure mode off.",
          );
        if (name === "acknowledge_import_review_batch")
          return request("/api/send", { expected_token: args.pending_token });
        const u = args.update;
        const subject =
          !u || u.kind === "approve"
            ? "approval"
            : u.kind === "mapping" || u.subject_kind === "account"
              ? "account:" + u.subject_id
              : u.kind === "postings"
                ? "postings:" + u.subject_id
                : u.subject_kind === "statement"
                  ? "source"
                  : "row:" + u.subject_id;
        const state = await request("/api/save", {
          expected_token: u?.expected_etag ?? args.expected_etag,
          source_file: args.source_file,
          run_id: args.run_id,
          subject,
          kind: u?.kind,
          value: u?.value,
        });
        return {
          source_file: args.source_file,
          run_id: args.run_id,
          etag: state.batch.token,
          review_digest: state.batch.token,
        };
      }
      if (name === "export_import_review")
        throw Error(
          "HTML export requires the plugin runtime. Use Saved JSON / diffs in this experiment.",
        );
      return demoResult(await request("/api/state"), name, args);
    },
    async continue() {
      /* Local simulation. The acknowledgement records the send. */
    },
  };
}
