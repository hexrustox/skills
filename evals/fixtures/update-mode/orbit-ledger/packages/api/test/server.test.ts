import { describe, expect, it } from "vitest";
import { toJson } from "../src/server.js";

describe("toJson", () => {
  it("keeps cents as strings on the wire", () => {
    const entry = {
      id: "entry-1",
      debit: { account: "cash", amount: { value: "100" } },
      credit: { account: "revenue", amount: { value: "100" } },
    };

    expect(toJson(entry)).toContain('"value":"100"');
  });
});
