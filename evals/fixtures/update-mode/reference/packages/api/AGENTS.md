# API package

This package exposes the ledger over HTTP. The OpenAPI contract at
`packages/api/openapi.yaml` is the route and payload authority; change the
contract before changing handlers.

For this package, run `pnpm --filter @orbit/api test`.

Repo-wide commands and boundaries live in the root `AGENTS.md`.
