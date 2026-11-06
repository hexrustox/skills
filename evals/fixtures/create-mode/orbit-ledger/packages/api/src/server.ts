import type { LedgerEntry } from "./generated/client.js";

export function toJson(entry: LedgerEntry): string {
  return JSON.stringify(entry);
}
