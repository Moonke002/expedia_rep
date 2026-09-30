# Expedia Rep

Expedia Rep is a classroom travel prototype with hotel search, demo accounts, personalized displayed rates, and simulated booking history. Vue sends actions to FastAPI; Python controllers read and write SQLite. No payment or real reservation occurs.

## Run locally

Use Python 3.10+ and a Node.js version supported by `frontend/package.json`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally <http://127.0.0.1:5173/>). Vite proxies `/api` to FastAPI at `http://127.0.0.1:8001` in this local setup because port 8000 is occupied by another service. The API also exposes `/health` and `/docs`.

The backend loads the project-root `.env` through `backend/app/config.py`. The file is ignored by Git; keep `GEOAPIFY_API_KEY` there for backend Geoapify requests only. `/api/health` reports only whether the key is configured and never returns its value. Restart FastAPI after editing `.env` so the new configuration is loaded. The Leaflet map uses OpenStreetMap tiles and has no browser-visible tile credential.

## Data and behavior

- On the first data request, the backend creates `backend/expedia.sqlite3` and seeds hotels, fixed-date trips, demo travelers, and sample bookings from the four CSVs in `backend/`. Trips reference hotels through `hotel_id`; bookings reference travelers and trips through `user_id` and `trip_id`. The CSVs are a starting dataset, not a cap on database rows. All subsequent application reads and writes use SQLite, including search and traveler lists.
- If a previous `backend/bookings.sqlite3` exists when the new database is first created, its booking changes are copied into the new database; the old file is left untouched. Both local databases are ignored by Git. To preserve your history, back up `expedia.sqlite3` before replacing or deleting it. A fresh database seeds again from CSV, optionally importing the legacy file.
- Hotel-name search is case-insensitive; a blank search lists all stays. City and nightly-price filters and price sorting operate on the returned stays.
- The ZIP demonstration accepts a five-digit U.S. ZIP, including leading zeros. FastAPI verifies the Geoapify postcode match first, then searches Geoapify hotels within 5 km of the returned postcode coordinates; an unresolved ZIP never falls back to another location.
- The ZIP panel distinguishes invalid input, an unresolved ZIP, a failed request, a successful result, and a resolved ZIP with no nearby hotels. Provider failures appear as errors rather than empty results.
- ZIP results show the provider-returned hotels in a selectable list and Leaflet map. Selecting a hotel in either view highlights the same result in both; the map center marks the verified ZIP search point. No price, availability, rating, or booking data is inferred for these Geoapify places.
- New bookings get unique IDs without renumbering seeded IDs. Deleting a test booking removes only a booking created in the UI; supplied sample records are protected.
- Existing U001–U006 travelers have demo usernames `demo1`–`demo6`, all with the classroom-only password `DemoPass123!`. Use made-up credentials for new accounts; do not reuse a personal password. Registration rejects duplicate usernames (case-insensitive), assigns a unique user ID, and requires a separate sign-in. Passwords are salted and hashed in the local database. Sign-in uses a seven-day HttpOnly cookie backed by a stored session; logout revokes it. This is a local demo, not production authentication.
- Signed-in users can search for a stay and choose **Book this stay**. **Booking history** belongs to the signed-in account; a new booking can be read, cancelled while retained, and deleted after an in-page confirmation. Guests may search at base rates but cannot manage bookings.
- Each signed-in hotel-name search is recorded in one SQLite search-history table. For the same user and normalized query (trimmed and case-insensitive) on the same **UTC calendar day**, searches 1–3 show the stored base nightly rate; search 4 and later show a **single 20% increase**. Other queries, users, and the next UTC day have independent counts. Blank searches are recorded but never increase the count. A displayed surge never changes the hotel's base rate. This is an instructional urgency assumption, not real demand or inventory pricing.
- The two-month calendar is for planning only. It does not filter the fixed-date offers. Stay totals multiply the returned displayed nightly rate by the number of nights; taxes and fees are unavailable.

## Checks

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

Browser checks: `Trail` returns Valley Trail Inn; an absent name shows a clear no-results message. Sign in as `demo1` and search `Trail` four times to see $100 for the first three searches and $120 from the fourth onward, unless that account has already made matching searches today. Another account's first search remains $100. A test booking can be created, seen after reload, cancelled while retained, then deleted from history. Automated backend tests use a temporary SQLite database and do not alter local history.

## Project notes

- [Project rules](AGENTS.md)
- [Design and UI research note](docs/design.md)
- [Search screenshot](docs/screenshots/part-2-search.png) and [booking-history screenshot](docs/screenshots/part-2-history.png)
- [Selected prompts](prompts/)
- [Current handoff](handoffs/current.md)
- [Part report](report.md)

The supplied data has no hotel photos, ratings, amenities, room inventory, flights, taxes, or savings. The interface uses illustrations and labels the booking flow as a simulation.
