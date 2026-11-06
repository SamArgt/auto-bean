import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { demoResult } from "./bridge.mjs";
function state(stage = "") {
  const root = new URL(
    "./fixtures/" + (stage ? stage + "/" : ""),
    import.meta.url,
  );
  const read = (p) => JSON.parse(readFileSync(new URL(p, root)));
  const session = read("session.json");
  return {
    session,
    status: read("import-status.json"),
    documents: session.groups.map((g) => read(g.parsed_group)),
    directory: "/synthetic",
    batch: { token: "v1", answers: {}, approvals: [], pending: {} },
  };
}
test("adapter maps saved answers into row, sidebar and session receipt counts", () => {
  const s = state();
  const source = s.documents[0].statements[0];
  const row = source.extracted_records.find(
    (r) => r.review.state === "needs_input",
  );
  const args = {
    source_file: source.source_file,
    account_id: row.account_id,
    needs_input: true,
  };
  const before = demoResult(s, "list_import_transactions", args);
  assert.equal(before.received_inputs.length, 0);
  s.batch.answers[source.source_file + "#row:" + row.record_id] =
    "Expenses:Dining";
  const after = demoResult(s, "list_import_transactions", {
    ...args,
    offset: 100,
  });
  assert.deepEqual(after.received_inputs, [row.record_id]);
  assert.equal(after.rows.length, 0);
  assert.ok(
    demoResult(s, "read_import_statement", args).received_inputs.includes(
      "transaction:" + row.record_id,
    ),
  );
  assert.equal(
    demoResult(s, "read_import_session").statements[0].needs_input,
    0,
  );
});
test("account-only fixtures expose zero transactions without losing mapping evidence", () => {
  const s = state("accounts");
  for (const g of s.documents)
    for (const source of g.statements) {
      assert.equal(
        demoResult(s, "list_import_transactions", {
          source_file: source.source_file,
        }).total,
        0,
      );
      assert.ok(
        demoResult(s, "read_import_statement", {
          source_file: source.source_file,
        }).statement_metadata.accounts.length,
      );
    }
});
