# Expedia Rep

Expedia Rep is a small Expedia replication exercise. Part 1 presents an Expedia-inspired “Choose stay” experience where a user searches hotel names and reviews available fixed-date stays from supplied CSV data.

## Repository layout

```text
backend/
  app/
    main.py          # FastAPI application, CSV join, and search endpoint
  hotels.csv         # supplied hotel records (add locally)
  trips.csv          # supplied stay records (add locally)
  requirements.txt   # Python dependencies
frontend/
  src/               # Vue search, filters, and stay-card results
  package.json       # Node dependencies and scripts
  vite.config.js     # Vite configuration
docs/design.md       # Part 1 design responsibilities
prompts/             # selected prompts
handoffs/current.md  # current handoff state
```

## Setup

Backend dependencies are installed in the project-local `backend/.venv`.
Frontend dependencies are installed in the project-local `frontend/node_modules`.

Place the supplied `hotels.csv` and `trips.csv` files directly in `backend/`. Both files must contain `hotel_id`; the hotel file must also contain a hotel-name column named `hotel_name`, `name`, or `hotel`. The supplied files are included in this checkout.

### Backend

From `backend/`, create and activate a virtual environment, then install the declared dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at <http://127.0.0.1:8000>. The search endpoint is `GET /api/hotels/search?hotel_name=...`; `/health` and `/docs` are also available.

### Frontend

From `frontend/`, install dependencies and start the Vite development server:

```powershell
npm install
npm run dev
```

The frontend will print its local development URL in the terminal.

The Vite development server proxies `/api` requests to the backend at `http://127.0.0.1:8000`.

## Part 1 behavior

Enter a hotel name present in `backend/hotels.csv`. Matching stays joined by `hotel_id` appear as Expedia-inspired cards with the hotel name, location, trip name, dates, nightly rate, and calculated stay total. City and nightly-price filters operate on the returned data.

The screen includes the visual regions represented by the supplied references: a “Choose stay” header, date/traveler summary, search control, filter row, repeated result template, and price module.

The supplied CSVs do not contain real property photos, ratings, amenities, flights, previous prices, savings, traveler accounts, saved trips, or booking records. The UI uses labeled CSS placeholders for photos and explicitly identifies savings as unavailable rather than inventing those values.

Expected no-result search: enter a name absent from the supplied data; the page shows `No matching hotel stays were found.`

Observed status: direct Oxlint/ESLint checks and the production build pass. In the browser, `Harbor Lantern Hotel` returned two stay cards (`T001` and `T009`), the Boston city filter remained functional, and `No Such Hotel` displayed `No matching hotel stays were found.`

The requested manual VS Code scan could not be completed because no controllable VS Code window is available in this environment. Commit and GitHub push remain pending that review.

## Development notes

- Keep backend and frontend dependencies isolated in their respective directories.
- Add environment-specific configuration through ignored `.env` files and document required variables here.
- Update this README when setup or project boundaries change.
