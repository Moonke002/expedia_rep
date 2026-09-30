# Project rules

## Scope

- The backend is a Python FastAPI application under `backend/`.
- The frontend is a Vue application built with Vite under `frontend/`.
- Keep backend-only and frontend-only code in their respective directories.
- Keep `hotels.csv` and `trips.csv` in `backend/`; join records only through `hotel_id`.
- Keep the supplied `users.csv` and `bookings.csv` in `backend/`. These four CSVs seed `backend/expedia.sqlite3` once; application reads and writes then use SQLite only. Do not treat the seed count as a limit. Preserve the ignored legacy `backend/bookings.sqlite3` when migrating prior local booking changes.

## Changes

- Keep the initial implementation small and focused on the requested feature.
- Prefer clear, typed Python and idiomatic Vue Composition API patterns.
- Do not commit secrets, local virtual environments, `node_modules/`, build output, or local `.env` files.
- Update `README.md` when setup commands, dependencies, or repository structure change.
- Keep the design note in `docs/`, selected prompts in `prompts/`, and `handoffs/current.md` concise and aligned with the submitted work.

## Verification

- Before submitting backend changes, run the relevant FastAPI checks or start the app and verify `/health`.
- Before submitting frontend changes, run the relevant Vite build or development checks.
- For Part 1, manually inspect changed files in VS Code and verify one matching and one non-matching browser search when the CSV data is available.
- For Part 2, verify search, calendar behavior, and every booking CRUD action through the frontend. A cancelled booking must remain in history; deleting a test booking must remove it.
- For SQLite/MVC changes, verify all four seeded tables, referential integrity, post-seed SQLite-only reads, persistence across restart, and unique new booking IDs.
- For accounts/pricing changes, preserve existing user and booking IDs, use made-up demo credentials only, keep booking access bound to the signed-in user, and verify the fourth-search threshold, normalization, separate users/queries, UTC rollover, and unchanged stored base rates.
- Do not install dependencies unless the task explicitly requests it.
