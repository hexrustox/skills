export type Cents = bigint & { readonly __brand: unique symbol };

export const Money = {
  fromCents(value: bigint): Cents {
    return value as Cents;
  },

  toWire(value: Cents): string {
    return value.toString();
  },

  add(left: Cents, right: Cents): Cents {
    return (left + right) as Cents;
  },
};
