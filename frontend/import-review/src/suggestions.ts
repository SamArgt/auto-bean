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
