# AGENTS.md

> **Project:** Orbit Ledger is the double-entry ledger behind Orbit's invoicing
> product. It records immutable postings and exposes them through an HTTP API.
> Money correctness is the domain's first constraint.

## Toolchain

| Intent | Command | Authority |
| --- | --- | --- |
| Install | `pnpm install` | `packageManager` in `package.json` |
| Lint | `pnpm lint` | `biome.json` |
| Type check | `pnpm typecheck` | `tsconfig.json` |
| Test | `pnpm test` | package scripts |
| Migrate | `pnpm db:migrate` | `scripts/migrate.mjs` |
| Regenerate the API client | `pnpm codegen` | `packages/api/package.json` |

CI runs `pnpm codegen` and then checks the generated client for drift, so run
`pnpm codegen` after editing `packages/api/openapi.yaml` and commit the result.
CI also runs `pnpm db:migrate` before `pnpm test`; do the same locally when the
database is empty.

## Judgment Boundaries

**Ask**

- Before running `pnpm db:migrate` against production. The script refuses unless
  `ALLOW_PROD_MIGRATION=1` is set deliberately after review.

**Always**

- Use `@orbit/money` and `Money.fromCents()` for every monetary value. Store and
  compute integer cents; serialize cents as a decimal string on the wire. Never
  pass a monetary string through `Number()`.
- Run `pnpm lint`, `pnpm typecheck`, and `pnpm test` before finishing.
- Run `pnpm codegen` after changing the OpenAPI contract, and commit the
  regenerated client.

**Never**

- Do not hand-edit files under `packages/api/src/generated`; they are generated
  by `pnpm codegen`.
- Do not import `@orbit/api` from `@orbit/ledger`; the ledger owns the domain and
  must not depend on the transport.
