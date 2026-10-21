export type Binding = { workspace: string; session_id: string };
export type Posting = {
  account: string;
  amount: string;
  currency: string;
  cost?: string;
  price?: string;
};
export type ReviewUpdate = {
  kind: "mapping" | "postings" | "answer" | "approve" | "reject";
  subject_id: string;
  subject_kind?: "statement" | "account" | "transaction";
  value?: string | Posting[];
  expected_etag: string;
  review_digest?: string;
};
export type SavedReview = {
  source_file: string;
  etag: string;
  review_digest: string;
};
export type SavedPrice = {
  run_id: string;
  etag: string;
  review_digest: string;
};
export type Approval = { digest: string; approved_at: string; origin: "panel" };
export type Validation = {
  stage: "review" | "written";
  state: "passed" | "failed";
  checked_at: string;
  digest: string;
  ledger_hashes: Record<string, string>;
  records_checked: number;
  balances: {
    account_id: string;
    date: string;
    currency: string;
    expected: string;
    actual: string;
    state: "matched" | "mismatch";
  }[];
  errors: string[];
};
export type Balance = {
  date: string;
  amount: string;
  currency: string;
  source_reference?: string;
};
export type SourceAccount = {
  review?: AccountDecision;
  account_id: string;
  account_name?: string;
  account_owner?: string;
  opening_balance?: Balance | null;
  closing_balance?: Balance | null;
  available_balance?: Balance | null;
};
export type AccountDecision = {
  suggestions?: string[];
  answer?: string;
  state: string;
  ledger_account?: string;
  rationale: string;
  proposed_directives?: string[];
  reconciliation?: {
    date: string;
    currency: string;
    ledger_amount?: string;
    difference?: string;
    provenance: string;
    state: string;
  }[];
};
export type Detail = {
  source_file: string;
  etag: string;
  extraction_state: string;
  statement_metadata: { accounts: SourceAccount[] };
  processing: {
    warnings: string[];
    failure_reason?: string;
    needs_input?: boolean;
    suggestions?: string[];
    answer?: string;
  };
  review_digest: string;
  approval: Approval | null;
  validation: Validation | null;
  validation_current: boolean | null;
};
export type Transaction = {
  record_id: string;
  account_id: string;
  transaction_date: string;
  description: string;
  amount: string;
  currency: string;
  source_reference: string;
  review?: {
    suggestions?: string[];
    answer?: string;
    state: string;
    postings: Posting[];
    rationale: string;
    findings?: string[];
    disposition: string;
    existing_transaction?: { path: string; line: number };
    linked_records?: {
      source_file: string;
      account_id: string;
      record_id: string;
    }[];
  };
};
export type Page = {
  etag: string;
  total: number;
  offset: number;
  rows: Transaction[];
};
export type PriceRun = {
  run_id: string;
  review_digest: string;
  approval?: Approval;
  validation?: Validation;
  validation_current: boolean | null;
  requested_date: string;
  state: string;
  required_commodities: string[];
  coverage: string[];
  preflight: string;
  preflight_job_count: number;
  execution: {
    state: string;
    exit_code: number | null;
    duration_seconds: number;
    stderr_summary: string;
    started_at?: string;
    ended_at?: string;
  };
  detail: string;
  jobs: {
    commodity: string;
    source: string;
    requested_date: string;
    quote_date?: string;
    outcome: string;
    directive?: string;
    detail?: string;
  }[];
};
export type Overview = Binding & {
  etag: string;
  statements: {
    source_file: string;
    status: string;
    updated_at: string | null;
    etag: string | null;
    extraction_state: string | null;
    needs_input: number;
    error: string | null;
  }[];
  price_runs: PriceRun[];
};
export interface Bridge {
  call<T>(name: string, args: Record<string, unknown>): Promise<T>;
  continue(sessionId: string, sourceFile: string): Promise<void>;
  openFile?(path: string): Promise<void>;
}
