# Expedia Rep — Part 1

## Repository and commit

[GitHub repository](https://github.com/Moonke002/expedia_rep). The submitted Part 1 commit is [`52fdaaa0274f46a766d1b6faf09df1bb8c4629fd`](https://github.com/Moonke002/expedia_rep/commit/52fdaaa0274f46a766d1b6faf09df1bb8c4629fd), titled `Part 1: add Expedia stay search experience`.

## Implementation

The Vue frontend provides an Expedia-inspired “Choose stay” screen with hotel-name search, city and nightly-price filters, repeated stay cards, fixed dates, hotel location, nightly rate, and a calculated stay total. It uses CSS photo placeholders because the supplied data has no property photos.

FastAPI exposes `/health` and `/api/hotels/search`. The backend reads `backend/hotels.csv` and `backend/trips.csv`, matches the hotel name, and joins hotel records to available stays through `hotel_id`. The frontend calls the endpoint through the Vite development proxy and renders the returned records.

## Verification

- Backend smoke check: `/health` returned HTTP 200 with `{"status":"ok"}`; the matching search for `Harbor Lantern Hotel` returned two records, `T001` and `T009`, both joined to `H001`; `No Such Hotel` returned zero records.
- Frontend smoke check: the Vite root returned HTTP 200, the browser rendered two stay cards for `Harbor Lantern Hotel`, and the city filter operated on the results.
- No-result browser check: searching for `No Such Hotel` displayed `No matching hotel stays were found.`
- Quality checks: Oxlint, ESLint, and the production build all passed.
- Stress check: 300 concurrent matching API requests, 200 concurrent no-result API requests, and 100 concurrent frontend requests completed with zero failures. API matching p95 latency was 321.9 ms; no-result p95 was 38.1 ms; frontend p95 was 31.3 ms.
- Manual review: a VS Code scan was attempted but could not be completed because no controllable VS Code window was available in the execution environment. The changed files were inspected through the available workspace file view instead.
- Screenshot status: no instructor-accessible browser screenshot file is currently stored in the repository. The browser checks were performed live at `http://127.0.0.1:5173/`; the supplied PNGs are visual references, not screenshots of this implementation.

## Project context and next steps

- [README.md](https://github.com/Moonke002/expedia_rep/blob/master/README.md) — setup, behavior, and limitations.
- [AGENTS.md](https://github.com/Moonke002/expedia_rep/blob/master/AGENTS.md) — project rules.
- [Design note](https://github.com/Moonke002/expedia_rep/blob/master/docs/design.md) — frontend, FastAPI, and backend responsibilities.
- [Selected prompt](https://github.com/Moonke002/expedia_rep/blob/master/prompts/part-1.md) — Part 1 scope.
- [Current handoff](https://github.com/Moonke002/expedia_rep/blob/master/handoffs/current.md) — checked work, limitations, and next task.

Remaining limitations are the absence of real photos, ratings, amenities, flight inventory, savings, traveler accounts, saved state, and booking records in the supplied CSV data. The next task is to complete the manual VS Code review, add instructor-accessible browser screenshots if required, and then extend the data model only when the next part supplies those fields and behaviors.
