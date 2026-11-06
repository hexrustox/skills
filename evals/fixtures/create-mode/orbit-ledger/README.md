# Orbit Ledger

Orbit Ledger is the double-entry ledger behind Orbit's invoicing product. It
records money movements as immutable postings and exposes them through an HTTP
API.

## Quick start

Requires Node.js 22 and pnpm.

```bash
npm install
npm test
npm run start
```

The API listens on <http://localhost:3000>. The ledger package is in
`packages/ledger`; the HTTP API is in `packages/api`.

## Money

Money is easy to get wrong. Read [ADR 0002](docs/adr/0002-money-in-cents.md)
before changing anything that touches amounts.

## More docs

- [Package boundaries](docs/adr/0001-package-boundaries.md)
- [OpenAPI contract](packages/api/openapi.yaml)
