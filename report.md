# Expedia Rep — Assignment 2, Part 2

## Project access and submission state

- **Repository:** [Moonke002/expedia_rep](https://github.com/Moonke002/expedia_rep)
- **Working branch:** `rag_integration`
- **Last committed baseline:** [`d03836e`](https://github.com/Moonke002/expedia_rep/commit/d03836e475d5af41ceed3560338e9eda09dfab27). The RAG and ZIP integration changes described here are in the current working tree; commit or push them before submitting if the instructor needs to review the latest version on GitHub.
- **Setup and run instructions:** [README.md](README.md)
- **Design and MVC responsibilities:** [docs/design.md](docs/design.md)
- **RAG workflow evidence:** [docs/rag-context.md](docs/rag-context.md) and [docs/rag-verification.md](docs/rag-verification.md)
- **Selected implementation prompt:** [prompts/rag-integration.md](prompts/rag-integration.md)

The frontend is Vue/Vite in `frontend/`; the FastAPI backend and SQLite database logic are in `backend/`. The project-root `.env` is ignored by Git. Geoapify uses `GEOAPIFY_API_KEY`; OpenAI uses the separate `OPEN_AI` variable, which the backend passes explicitly to the SDK. The API key is never included in the frontend, report, prompts, screenshots, or this evidence.

## Research and early design

The design follows the supplied October 1 [Local Hotel Storage and Manual Verification activity](https://psu.instructure.com/courses/2484533/pages/in-class-activity-local-hotel-storage-and-manual-verification) and its [graded companion](https://psu.instructure.com/courses/2484533/assignments/18765499), then extends that foundation using the supplied IST 402 RAG lecture's retrieval-then-generation workflow. The [design note](docs/design.md) describes the existing MVC path and the new assistant's path through Vue, FastAPI, the database controller, and SQLite. The [selected RAG prompt](prompts/rag-integration.md) records the schema, read-only query, join, result-bound, date, and answer-grounding constraints used during implementation.

The original chatbot mockup supplied for this report is [travel-assistant-original-mockup.png](docs/assets/travel-assistant-original-mockup.png). It shows the initial full-page assistant concept; the implementation was later adapted into a floating corner panel so it remains available over the hotel-search view. The repository also includes [the Part 2 search screenshot](docs/screenshots/part-2-search.png) and [the booking-history screenshot](docs/screenshots/part-2-history.png) as visual references for the existing application.

## Application foundation

The Part 2 feature extends the existing Expedia Rep application rather than replacing its supplied data or search flow:

- Four supplied CSVs seed the assignment's hotel, trip, user, and booking tables once. Existing IDs and relationships remain intact; application reads and writes use SQLite after seeding.
- ZIP search checks saved API hotels for the requested ZIP first. If none are saved there, the backend verifies the ZIP and searches Geoapify near that verified location. Add to Local and Remove from Local preserve provider identity and ZIP context.
- Saving an API hotel creates dated nightly rows with clearly labeled **simulated course rates and availability**. These values are fictional examples, not provider quotes or real inventory.
- Existing hotel-name search, ZIP lookup, list/map selection, planning calendar, account, and booking behavior remain part of the application. The assistant only retrieves and explains saved catalog data; it does not book or change records.

## Retrieval and answer workflow

The Travel assistant accepts a natural-language hotel question in the floating chat panel. `frontend/src/api/chat.js` keeps request handling separate from `frontend/src/components/TravelChat.vue` presentation. The browser sends the message and optional conversation ID to the application's `POST /api/chat` endpoint; it does not send a provider credential.

FastAPI asks the configured OpenAI model for a focused SQLite `SELECT`, providing the user's question, the relevant schema, and query rules. The model cannot connect to SQLite. The backend checks the proposal, then executes it through a read-only connection with an SQLite authorizer restricted to `saved_hotels`, `saved_hotel_zips`, and `demo_hotel_nights`, a query time limit, and a 20-row bound. A second model request receives the original question, the accepted SQL, and only the returned rows. The Vue panel displays the question, proposed SQL, retrieved records, and grounded answer, with pending and failure states.

For date ranges, check-in is included and checkout is excluded. A multi-night total is supported only when each requested night has a returned record with rooms available; a missing night is insufficient data. Demo rates and availability remain labeled simulated course data.

## Live successful lookup

**Conversation ID:** `6164e904a68641fba122173f1cf28a60`

**Provider/model:** live OpenAI API calls using `gpt-6-luna`
**Question:** “Find available saved hotel rooms in ZIP 16802 for check-in October 10, 2026 and checkout October 12, 2026. List each night price and room count, and total.”

The model proposed this SQL, and the backend validated and executed it read-only:

```sql
SELECT h.hotel_id, h.name, h.address, n.stay_date, n.nightly_rate_cents, n.rooms_available
FROM saved_hotels AS h
JOIN saved_hotel_zips AS z ON z.hotel_id = h.hotel_id
JOIN demo_hotel_nights AS n ON n.hotel_id = h.hotel_id
WHERE z.postcode = '16802'
  AND n.stay_date >= '2026-10-10'
  AND n.stay_date < '2026-10-12'
  AND n.rooms_available > 0
ORDER BY h.hotel_id, n.stay_date
LIMIT 20;
```

Both joins use `hotel_id`: the first joins hotel identity to ZIP/location context, and the second joins hotel identity to nightly price and availability. At the time of the live exchange, the local query returned these rows:

| Hotel | ZIP | Night | Simulated nightly rate | Simulated rooms |
|---|---:|---|---:|---:|
| RAG Context Demo Inn | 16802 | 2026-10-10 | $125.00 | 4 |
| RAG Context Demo Inn | 16802 | 2026-10-11 | $150.00 | 2 |

**Displayed answer:** RAG Context Demo Inn had an available-room record for each requested night: October 10 at $125.00 with 4 rooms and October 11 at $150.00 with 2 rooms. The two-night total was $275.00. Checkout day was excluded, and the answer identified the rates and rooms as simulated course data.

**Expected vs observed:** Expected two nightly records, those same prices and room counts, and a $275.00 total. The live chatbot rows matched the direct read-only SQLite query recorded in [RAG context evidence](docs/rag-context.md), and the answer displayed those values. The fixture used for this demonstration was temporary and was removed after evidence collection; the saved conversation retains its question, SQL, retrieved rows, and answer.

## No-match and changed-date checks

The same conversation includes two further live model exchanges:

| Question | Expected | Observed |
|---|---|---|
| “For ZIP 16802, now compare check-in October 12, 2026 to checkout October 14, 2026. Show each available night, rate, rooms, and total.” | New half-open date filters and records for October 12 and 13. | The generated SQL changed the date range to `>= '2026-10-12'` and `< '2026-10-14'`. SQLite returned October 12 at $110.00 / 8 rooms and October 13 at $120.00 / 6 rooms. The answer totaled $230.00. |
| “Are any saved rooms available in ZIP 16802 for check-in October 14, 2026 and checkout October 15, 2026? If no rows match, explain that and do not suggest a specific alternative unless the database returned it.” | No matching rows; no invented hotel or price. | The generated query used the requested ZIP/date and `rooms_available > 0`; retrieval returned `[]`. The answer stated that no saved hotel matched and did not name an alternative or price. |

The full SQL, row values, and answers for these checks are in [docs/rag-context.md](docs/rag-context.md). These are historical live results from a temporary labeled fixture; that fixture is no longer in the saved-hotel catalog.

## Safety, failure, and persistence verification

Automated RAG safety checks use labeled mock model responses and an isolated `tmp_path` SQLite database, not the course database. A mock-proposed `DELETE FROM saved_hotels` is rejected before query execution and before the answer-generation request. The before/after snapshot of the protected course and saved-hotel tables is identical. The test also covers unauthorized table reads, multiple statements, unsafe SQLite functions, result bounds, empty results, partial-night records, and one repair attempt for a malformed read-only proposal.

**Expected vs observed:** a write or disallowed query must not execute or alter rows. The mock test observed rejection and an unchanged database snapshot. The failed conversation stores a timestamped user entry and an `error` entry; it has no assistant reply, so no successful answer is fabricated. The request and safety cases are documented in [docs/rag-verification.md](docs/rag-verification.md).

Conversation `6164e904a68641fba122173f1cf28a60` is stored in SQLite. A read-only inspection for this report found 10 timestamped messages (five user questions and five assistant replies), including the SQL and retrieved JSON on assistant entries. Earlier verification reloaded the same conversation after a page refresh and backend restart. The temporary hotel fixtures have been removed from the catalog; historical conversation evidence remains available.

## Verification summary

| Check | Expected | Observed evidence |
|---|---|---|
| Full RAG path | Question → proposed SQL → checked retrieval → second LLM request with records → displayed answer | Live browser exchange plus persisted SQL/rows/answer; mocked route test asserts two model calls and verifies the second call receives the original question, validated SQL, and retrieved rows. |
| Direct DB comparison | Same ZIP/date query returns the same records as the chat | Two October 10–11 rows matched during the live fixture check; direct query and result are preserved in `docs/rag-context.md`. |
| Date change | SQL filters and rows change with dates | October 12–13 returned two different nightly rows and a $230.00 total. |
| No match | Empty retrieval and no invented recommendation | October 14 returned `[]` and an explicit no-match answer without a suggested hotel or price. |
| Missing night | Do not claim a complete stay or total when a night is absent | Mock test returns a partial set and verifies that the second request is instructed to report insufficient data. |
| Disallowed SQL | Reject writes/unauthorized access and preserve database rows | Labeled mock tests reject `DELETE`, unauthorized reads, and multi-statement SQL; fixture table snapshots remain unchanged. |
| Failure history | Record user/error with no fabricated assistant message | Test asserts timestamped `user` and `error` roles and no assistant role. |
| Refresh/restart | Existing conversation can be loaded again | Same conversation ID was loaded after refresh/backend restart; current read-only inspection found 10 messages. |
| Credential isolation | Credentials stay on the backend | `.env` is Git-ignored; `OPEN_AI` is passed explicitly to the OpenAI client; frontend chat sends only message and conversation ID. |
| Existing application | Preserve seeded records, ZIP lookup and booking/search flows | Prior verification is recorded in `handoffs/current.md`; ZIP 19014 also resolved to Concord Township with nearby hotels in the live browser after the Geoapify key was updated. |

Earlier Part 2 browser checks also observed Valley Trail Inn for the matching `Trail` search and the expected no-results state for `No Such Hotel`. Booking verification created a test booking, reloaded it from history, cancelled it while retaining the record, and then deleted that test booking; the seeded B001–B006 records remained present. The saved-hotel workflow was checked for save, five simulated nightly rows, remove, and absence after removal. These checks and the preserved database counts are summarized in [the current handoff](handoffs/current.md).

Backend verification recorded for this branch includes 13 focused RAG/config/schema checks using mock responses and a six-test Geoapify suite. The Vue production build passed. The earlier full application checks, database counts, booking CRUD, and integrity results are summarized in [handoffs/current.md](handoffs/current.md). The embedded browser does not expose a Network panel; the application request was confirmed through FastAPI logs and source inspection of the frontend request body.

## Recorded demonstration

The [final RAG demonstration recording](docs/assets/rag-final-demo.mp4) shows the completed application workflow. The [earlier ZIP lookup recording](docs/assets/zip-lookup-demo.mp4) separately demonstrates postcode search, the hotel list, and map behavior.

<video controls width="720" src="docs/assets/rag-final-demo.mp4">
  Your browser does not support embedded video. [Watch the final RAG demonstration](docs/assets/rag-final-demo.mp4).
</video>

## AI use disclosure

OpenAI's `gpt-6-luna` model is used at runtime for two tasks: proposing a read-only SQL query and composing an answer from the question and retrieved local rows. The application validates and executes SQL locally; the model does not access SQLite directly. Automated failure and safety tests use explicitly labeled mock responses rather than live model calls. AI assistance was also used during implementation and report preparation. The API credential remains in the ignored backend environment file and is not included in this report or frontend assets.

## Limitations

Nightly price and room data are simulated classroom records, not live inventory. A missing local record cannot establish that an actual hotel is sold out or available. The assistant only knows saved API hotels and their local ZIP/date records. Booking, payment, and inventory reservation remain simulations.
