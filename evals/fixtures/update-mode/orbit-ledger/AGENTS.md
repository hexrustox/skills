# AGENTS.md

> **Project:** Orbit Ledger is the double-entry ledger behind Orbit's invoicing
> product. It records immutable postings and exposes them through an HTTP API.
> Money correctness is the domain's first constraint.

## Quick start

Requires Node.js 22 and pnpm 9.12.0.

```bash
npm install
npm test
npm run start
```

The API listens on http://localhost:3000.

## Toolchain

| Intent | Command | Authority |
| --- | --- | --- |
| Install | `pnpm install` | `packageManager` in `package.json` |
| Lint | `pnpm lint` | `biome.json` |
| Type check | `pnpm typecheck` | `tsconfig.json` |
| Test | `pnpm test` | package scripts |
| Migrate | `pnpm db:migrate` | `scripts/migrate.mjs` |
| Regenerate the API client | `pnpm codegen` | `packages/api/package.json` |

## Code style

Biome enforces 2-space indentation and single quotes. Write clean code, use
meaningful variable names, follow best practices, and be careful with money.

Before every edit, read `docs/architecture.md` for the full design.

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
