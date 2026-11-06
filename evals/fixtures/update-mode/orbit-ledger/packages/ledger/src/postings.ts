import { Money, type Cents } from "@orbit/money";

export interface Posting {
  readonly account: string;
  readonly amount: Cents;
}

export interface LedgerEntry {
  readonly id: string;
  readonly debit: Posting;
  readonly credit: Posting;
}

export function createEntry(id: string, debit: Posting, credit: Posting): LedgerEntry {
  if (debit.amount !== credit.amount) {
    throw new Error("posting is unbalanced");
  }

  return { id, debit, credit };
}

export function sum(entries: readonly LedgerEntry[]): Cents {
  return entries.reduce(
    (total, entry) => Money.add(total, entry.debit.amount),
    Money.fromCents(0n),
  );
}
