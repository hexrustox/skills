# ADR 0002: Represent money as integer cents

## Status

Accepted.

## Context

Floating point arithmetic loses precision: `0.1 + 0.2` is not `0.3`. A ledger
cannot tolerate that. JavaScript's `number` is an IEEE-754 double, and
`JSON.parse` turns every JSON number into one, so a monetary value that crosses
the wire as a JSON number can silently lose cents.

## Decision

- Store and compute money as integer cents. The ledger uses `bigint` through
  the `Cents` type in `@orbit/money`; database columns are `BIGINT`.
- Use `Money.fromCents()` to construct a value. Never construct money from a
  float or from `Number`.
- The HTTP API serializes cents as a decimal string, never as a JSON number.
  The `Money` schema in `packages/api/openapi.yaml` is the authority for the
  wire shape.
- Clients must parse the string with a decimal library. Do not pass it through
  `Number()` or `parseInt()`.

## Consequences

Every boundary that converts between storage, domain, and wire formats has to
be explicit. The extra conversion is cheaper than a rounding bug in a ledger.
