# Expedia Rep — Part 2

## Repository and commit

[GitHub repository](https://github.com/Moonke002/expedia_rep). The reviewed Part 2 work is merged into `main` at [`79cc074a1571149602fcc298f71ba2669c962687`](https://github.com/Moonke002/expedia_rep/commit/79cc074a1571149602fcc298f71ba2669c962687). The Part 1 checkpoint remains preserved at [`52fdaaa`](https://github.com/Moonke002/expedia_rep/commit/52fdaaa).

## Implementation

The Vue frontend provides hotel search, filters, simulated booking, booking history, demo sign-in, account creation, and logout. FastAPI exposes authentication, search, pricing, and user-bound booking endpoints. Python controllers seed the supplied CSV records into SQLite once, then use SQLite for application reads and writes. Search history drives the classroom 20% surge display after the fourth matching normalized query in a UTC day without changing stored base rates.

## Verification

- Backend smoke test: `backend/.venv/Scripts/python.exe -m pytest -q` passed with 6 tests. Two dependency deprecation warnings were reported; no test failed.
- Frontend checks: Oxlint, ESLint, and `npm run build` passed.
- Runtime checks: `GET /health` returned HTTP 200 with `{"status":"ok"}`; the Vite page returned HTTP 200.
- Browser matching search: searched `Trail`. Expected one matching stay; observed Valley Trail Inn and one stay at the $100 base rate.
- Browser no-results search: searched `No Such Hotel`. Expected no matches; observed `0 stays` and `No matching hotel stays were found.`
- Browser account/history smoke test: signed in as `demo1`, opened Booking history, and observed four records belonging to that account. The seeded cancelled records remained visible.
- SQLite integrity: observed 8 hotels, 12 trips, 6 users, 8 bookings, and 26 search-history records; the seed marker was present, all supplied booking IDs occurred once, and `PRAGMA foreign_key_check` returned no violations.
- `git diff --check` passed. No source files or dependency declarations were changed during this smoke-test pass; only `report.md` and the aligned current handoff were updated.

## Project context and next steps

- [README.md](https://github.com/Moonke002/expedia_rep/blob/79cc074a1571149602fcc298f71ba2669c962687/README.md) — setup, run, and verification instructions.
- [AGENTS.md](https://github.com/Moonke002/expedia_rep/blob/79cc074a1571149602fcc298f71ba2669c962687/AGENTS.md) — project rules.
- [Design note](https://github.com/Moonke002/expedia_rep/blob/79cc074a1571149602fcc298f71ba2669c962687/docs/design.md) — frontend, FastAPI, and backend responsibilities.
- [Selected prompts](https://github.com/Moonke002/expedia_rep/tree/79cc074a1571149602fcc298f71ba2669c962687/prompts/) and [current handoff](https://github.com/Moonke002/expedia_rep/blob/79cc074a1571149602fcc298f71ba2669c962687/handoffs/current.md).

Remaining limitations are intentional classroom-demo boundaries: shared demo credentials, local SQLite, simulated bookings, no payments, inventory reservation, account recovery, real media, flights, taxes, or fees. The next task is instructor review of the account/pricing flow and a decision about whether to expand catalog management or harden authentication and pricing for production use.
