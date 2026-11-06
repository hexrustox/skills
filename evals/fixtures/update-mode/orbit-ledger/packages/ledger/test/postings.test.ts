import { Money } from "@orbit/money";
import { describe, expect, it } from "vitest";
import { createEntry } from "../src/postings.js";

describe("createEntry", () => {
  it("rejects an unbalanced entry", () => {
    const debit = { account: "cash", amount: Money.fromCents(100n) };
    const credit = { account: "revenue", amount: Money.fromCents(99n) };

    expect(() => createEntry("entry-1", debit, credit)).toThrow("unbalanced");
  });
});
