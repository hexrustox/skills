#!/usr/bin/env node

if (!process.env.DATABASE_URL) {
  console.error("DATABASE_URL is required. Copy .env.example to .env and load it.");
  process.exit(1);
}

console.log("Seeding the development database.");
