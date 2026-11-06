import { expect, test } from "vitest";
import { categorySuggestions, categoryLabel } from "./src/suggestions";

test("category choices preserve ranking and never turn prose into an approval", () => {
  expect(
    categorySuggestions([
      "Confirm hotel, spa or restaurant?",
      "Expenses:Travel:Lodging for a hotel; Expenses:Food:Dining for meals",
      "Expenses:Travel:Lodging",
      "Income:Salary",
      "Expenses:Travel:Lodging",
      "Assets:Bank:Savings",
    ]),
  ).toEqual([
    "Expenses:Travel:Lodging",
    "Income:Salary",
    "Assets:Bank:Savings",
  ]);
  expect(categoryLabel("Expenses:Travel:Lodging")).toBe(
    "Expense · Travel › Lodging",
  );
  expect(categoryLabel("Income:Salary")).toBe("Income · Salary");
});
