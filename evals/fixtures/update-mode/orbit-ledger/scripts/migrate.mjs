#!/usr/bin/env node

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  console.error("DATABASE_URL is required. Copy .env.example to .env and load it.");
  process.exit(1);
}

if (process.env.NODE_ENV === "production" && process.env.ALLOW_PROD_MIGRATION !== "1") {
  console.error("Refusing to migrate production. Set ALLOW_PROD_MIGRATION=1 only after review.");
  process.exit(1);
}

console.log(`Applying migrations to ${databaseUrl.replace(/:\/\/.*@/, "://***@")}`);
