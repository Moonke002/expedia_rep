# Expedia Rep — Part 2

## Repository and commit

[GitHub repository](https://github.com/Moonke002/expedia_rep). The reviewed Part 2 work is merged into `main` at [`79cc074a1571149602fcc298f71ba2669c962687`](https://github.com/Moonke002/expedia_rep/commit/79cc074a1571149602fcc298f71ba2669c962687). The Part 1 checkpoint remains preserved at [`52fdaaa`](https://github.com/Moonke002/expedia_rep/commit/52fdaaa). The ZIP lookup and map described below are later project updates than the referenced Part 2 commit.

## Implementation

The Vue frontend provides hotel search, filters, simulated booking, booking history, demo sign-in, account creation, and logout. FastAPI exposes authentication, search, pricing, and user-bound booking endpoints. Python controllers seed the supplied CSV records into SQLite once, then use SQLite for application reads and writes. Search history drives the classroom 20% surge display after the fourth matching normalized query in a UTC day without changing stored base rates.

The ZIP lookup demonstration accepts a five-digit U.S. ZIP code, including leading zeros. FastAPI sends Geoapify geocoding and Places requests using the backend-only key from the ignored project-root `.env`. It searches for nearby hotels only after Geoapify confirms the requested U.S. postcode, and centers the 5 km Places search on the returned coordinates. Vue displays the returned hotels in a list and a Leaflet map; selecting either a list entry or a map marker identifies the same hotel in both. Names, localities, coordinates, and distances come from the backend response, with missing optional locality labeled as unavailable. The ZIP results invent no prices, ratings, room availability, or booking confirmations. The map uses OpenStreetMap tiles without a browser-visible tile key.

**Screen recording:**

<video controls width="720" src="https://raw.githubusercontent.com/Moonke002/expedia_rep/main/docs/assets/zip-lookup-demo.mp4">
  Your browser does not support embedded video. [Download or watch the ZIP lookup demonstration](https://raw.githubusercontent.com/Moonke002/expedia_rep/main/docs/assets/zip-lookup-demo.mp4).
</video>

## Verification

- Backend smoke test: `backend/.venv/Scripts/python.exe -m pytest -q` passed with 6 tests. Two dependency deprecation warnings were reported; no test failed.
- Frontend checks: Oxlint, ESLint, and `npm run build` passed.
- ZIP demonstration: the frontend production build passed after adding Leaflet and the explicit invalid, unresolved, failed-request, results, and no-nearby-results states. The visible browser showed the verified ZIP 16802 response with 20 returned hotels and the map centered on its returned point; the maximum listed distance was 4.294 km.
- List/map selection: selecting Fairfield Inn & Suites in the list highlighted its map marker; selecting Sleep Inn on the map selected the matching list item.
- Configuration safety: `.env` matches the root `.gitignore` rule and is not tracked. The key value was not read during this check. Geoapify provider requests remain in FastAPI; the browser map uses uncredentialed OpenStreetMap tiles.
- Runtime checks: `GET /health` returned HTTP 200 with `{"status":"ok"}`; the Vite page returned HTTP 200.
- Browser matching search: searched `Trail`. Expected one matching stay; observed Valley Trail Inn and one stay at the $100 base rate.
- Browser no-results search: searched `No Such Hotel`. Expected no matches; observed `0 stays` and `No matching hotel stays were found.`
- Browser account/history smoke test: signed in as `demo1`, opened Booking history, and observed four records belonging to that account. The seeded cancelled records remained visible.
- SQLite integrity: observed 8 hotels, 12 trips, 6 users, 8 bookings, and 26 search-history records; the seed marker was present, all supplied booking IDs occurred once, and `PRAGMA foreign_key_check` returned no violations.

## Project context and next steps

- [README.md](https://github.com/Moonke002/expedia_rep/blob/79cc074a1571149602fcc298f71ba2669c962687/README.md) — setup, run, and verification instructions.
- [AGENTS.md](https://github.com/Moonke002/expedia_rep/blob/79cc074a1571149602fcc298f71ba2669c962687/AGENTS.md) — project rules.
- [Design note](https://github.com/Moonke002/expedia_rep/blob/79cc074a1571149602fcc298f71ba2669c962687/docs/design.md) — frontend, FastAPI, and backend responsibilities.
- [Selected prompts](https://github.com/Moonke002/expedia_rep/tree/79cc074a1571149602fcc298f71ba2669c962687/prompts/) and [current handoff](https://github.com/Moonke002/expedia_rep/blob/79cc074a1571149602fcc298f71ba2669c962687/handoffs/current.md).

Remaining limitations are intentional classroom-demo boundaries: shared demo credentials, local SQLite, simulated bookings, no payments, inventory reservation, account recovery, hotel photography, flights, taxes, or fees. The nearby hotel list reflects Geoapify Places results around one verified postcode point, not every address in the ZIP area. The next task is instructor review of the account/pricing flow and a decision about whether to expand catalog management or harden authentication and pricing for production use.
