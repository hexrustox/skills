# ADR 0001: Package boundaries

## Status

Accepted.

## Context

The ledger, the HTTP API, and the money primitive have different reasons to
change. Letting them import in any direction makes the domain depend on the
transport and makes money arithmetic impossible to test in isolation.

## Decision

- `@orbit/money` owns the money types and integer-cent arithmetic.
- `@orbit/ledger` owns postings and the ledger domain. It may depend on
  `@orbit/money`, but it must not import `@orbit/api`.
- `@orbit/api` may depend on both.

## Consequences

The dependency graph is acyclic and the ledger package can be tested without an
HTTP server.
