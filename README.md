# Expedia Rep

Expedia Rep is a classroom travel prototype with hotel search, demo accounts, personalized displayed rates, and simulated booking history. Vue sends actions to FastAPI; Python controllers read and write SQLite. No payment or real reservation occurs.

## Run locally

Use Python 3.10+ and a Node.js version supported by `frontend/package.json`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally <http://127.0.0.1:5173/>). Vite proxies `/api` to FastAPI at `http://127.0.0.1:8002` by default. The API also exposes `/health` and `/docs`.

If port 8002 is occupied by another process, start FastAPI on an unused port and set the same backend URL for Vite, for example `$env:EXPEDIA_API_TARGET = 'http://127.0.0.1:8003'` before `npm run dev`.

The backend loads the project-root `.env` through `backend/app/config.py`. The file is ignored by Git; keep `GEOAPIFY_API_KEY` there for Geoapify and `OPEN_AI` for the OpenAI SDK. This project passes `OPEN_AI` explicitly to `OpenAI(api_key=...)`; it does not rely on the SDK's `OPENAI_API_KEY` default. `OPENAI_MODEL` selects the model and currently defaults to `gpt-6-luna`. `/api/health` reports whether the key is configured and the model name, never the key value. Restart FastAPI after editing `.env` so the new configuration is loaded. The Leaflet map uses OpenStreetMap tiles and has no browser-visible tile credential.

## Data and behavior

- On the first data request, the backend creates `backend/expedia.sqlite3` and seeds hotels, fixed-date trips, demo travelers, and sample bookings from the four CSVs in `backend/`. Trips reference hotels through `hotel_id`; bookings reference travelers and trips through `user_id` and `trip_id`. The CSVs are a starting dataset, not a cap on database rows. All subsequent application reads and writes use SQLite, including search and traveler lists.
- Database initialization also applies additive, repeatable migrations for saved API hotel/night tables and `chat_conversations`/`chat_messages`. Conversation rows store timestamps, user/assistant/error roles, SQL proposals, and retrieved JSON rows. These migrations preserve the supplied hotel, trip, traveler, and booking records.
- Saved provider IDs and hotel details are separate from Assignment 1's sample `hotels`; each saved ZIP row preserves verified location context. Saving a hotel creates five fictional nightly records for October 10–14, 2026, defaulting to `$100.00` and 20 rooms. These are classroom values, not provider quotes or actual inventory. Night rows are unique by `(hotel_id, stay_date)` and reference their saved hotel.
- If a previous `backend/bookings.sqlite3` exists when the new database is first created, its booking changes are copied into the new database; the old file is left untouched. Both local databases are ignored by Git. To preserve your history, back up `expedia.sqlite3` before replacing or deleting it. A fresh database seeds again from CSV, optionally importing the legacy file.
- Hotel-name search is case-insensitive; a blank search lists all stays. City and nightly-price filters and price sorting operate on the returned stays.
- The ZIP demonstration accepts a five-digit U.S. ZIP, including leading zeros. FastAPI verifies the Geoapify postcode match first, then searches Geoapify hotels within 5 km of the returned postcode coordinates; an unresolved ZIP never falls back to another location.
- The ZIP panel checks saved hotels for the entered ZIP first. If local storage returns none, it calls the existing Geoapify search; local lookup failures stop with an error. Results are labeled `Saved locally` or `API results`. Saved results are only the records stored for that ZIP, not a complete area listing.
- ZIP results show hotels in a selectable list and Leaflet map. Selecting a hotel in either view highlights the same result in both; the map center marks the verified or saved ZIP search point. API results can be added to or removed from local storage by provider ID. Local results display dated demo rates and rooms with a classroom-data label; those values are not Geoapify prices or availability.
- The **Travel assistant** follows a two-request SQL RAG flow over saved local API hotels: OpenAI proposes a SELECT query from the saved-hotel schema, the backend validates and runs it read-only with a 20-row cap, then OpenAI answers from the returned records. ZIP, date, and room-availability filters follow the question; checkout is excluded, and missing nights are not treated as available. Only the three saved-hotel tables are queryable. Rates and availability are simulated course data, and the assistant cannot book or modify records.
- The chat view is in `frontend/src/components/TravelChat.vue`; `frontend/src/api/chat.js` calls `POST /api/chat` with the message and an optional conversation ID. It returns SQL and retrieved rows with the answer. The conversation ID alone is stored in browser local storage; messages, timestamps, and error entries are stored in SQLite and can be reloaded through `GET /api/chat/{conversation_id}`. A failed attempt is recorded as an `error` role and does not create an assistant reply.
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
.\node_modules\.bin\oxlint.cmd src vite.config.js
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
