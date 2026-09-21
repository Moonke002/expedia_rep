# Expedia Rep

Expedia Rep is a classroom travel prototype. Part 2 improves the hotel search screen and adds simulated booking history. All booking actions are available in the Vue interface. No payment or real reservation occurs.

## Run locally

Use Python 3.10+ and a Node.js version supported by `frontend/package.json`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally <http://127.0.0.1:5173/>). Vite proxies `/api` to FastAPI at `http://127.0.0.1:8000`. The API also exposes `/health` and `/docs`.

## Data and behavior

- `backend/hotels.csv` and `backend/trips.csv` are joined through `hotel_id`. Hotel-name search is case-insensitive; a blank search lists all stays. City and nightly-price filters and price sorting operate on returned stays.
- `backend/users.csv` defines demo travelers. `backend/bookings.csv` supplies initial booking history.
- The backend creates `backend/bookings.sqlite3` on the first history request, seeds the sample bookings once, and stores new bookings and status changes there. This local file is ignored by Git. Deleting a test booking removes only a booking created in the UI; supplied sample records are protected.
- Select a demo traveler, search for a stay, and choose **Book this stay**. The app opens **Booking history**, where the new record can be read, cancelled while retained, and deleted after an in-page confirmation.
- The two-month calendar is for planning only. It does not filter the fixed-date offers. Stay totals multiply the supplied nightly rate by the number of nights; taxes and fees are unavailable.

## Checks

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

Browser checks: `Trail` returns Valley Trail Inn; `Inn` returns Maple Square Inn, Liberty Lane Inn, and Valley Trail Inn; an absent name shows a clear no-results message. A test booking can be created, seen after reload, cancelled while retained, then deleted from history.

## Project notes

- [Project rules](AGENTS.md)
- [Design and UI research note](docs/design.md)
- [Search screenshot](docs/screenshots/part-2-search.png) and [booking-history screenshot](docs/screenshots/part-2-history.png)
- [Selected prompts](prompts/)
- [Current handoff](handoffs/current.md)
- [Part report](report.md)

The supplied data has no hotel photos, ratings, amenities, room inventory, flights, taxes, or savings. The interface uses illustrations and labels the booking flow as a simulation.
