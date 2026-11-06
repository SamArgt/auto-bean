import type { Transaction } from "./types";

// Only complete account names are safe to approve directly. Legacy questions
// and compound proposals remain evidence; never silently shorten their meaning.
export function categorySuggestions(values: string[] = []) {
  return [...new Set(values.map((value) => value.trim()))].filter((value) =>
    /^(Expenses|Income|Assets|Liabilities|Equity)(:[\p{Lu}\p{N}][\p{L}\p{N}-]*)+$/u.test(
      value,
    ),
  );
}
export function categoryLabel(value: string) {
  const [type, ...parts] = value.split(":");
  const label = (
    {
      Expenses: "Expense",
      Income: "Income",
      Assets: "Transfer / asset",
      Liabilities: "Liability",
      Equity: "Equity",
    } as Record<string, string>
  )[type];
  return label ? `${label} · ${parts.join(" › ")}` : value;
}

export function transactionStatus(row: Transaction, received = false) {
  const review = row.review;
  if (!review) return "Categorization pending";
  if (review.state === "needs_input" || review.disposition === "hold")
    return received ? "Input received" : "Needs input";
  return (
    (
      {
        post: "New entry",
        existing_duplicate: "Already in ledger",
        paired_transfer: "Internal transfer",
      } as Record<string, string>
    )[review.disposition] ?? "Under review"
  );
}
export function transactionCategories(row: Transaction) {
  const accounts = [
    ...new Set(row.review?.postings.map((p) => p.account) ?? []),
  ];
  const categories = accounts.filter((a) => /^(Expenses|Income):/.test(a));
  return categories.map(categoryLabel).join(" · ");
}
