# Project rules

## Scope

- The backend is a Python FastAPI application under `backend/`.
- The frontend is a Vue application built with Vite under `frontend/`.
- Keep backend-only and frontend-only code in their respective directories.
- Keep `hotels.csv` and `trips.csv` in `backend/`; join records only through `hotel_id`.

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
- Do not install dependencies unless the task explicitly requests it.
