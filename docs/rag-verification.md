# SQL RAG verification — October 8, 2026

## Expected and observed

| Check | Expected | Observed |
|---|---|---|
| Successful question | The model proposes a focused SELECT; the backend checks and runs it read-only; a second model request receives the original question and retrieved rows; the UI shows a grounded answer and evidence. | **Live model and browser:** asked “Find Codex RAG Validation Hotel in State College for check-in October 10, 2026 and checkout October 12, 2026. Show each night, simulated price, rooms available, and the stay total.” The browser displayed the generated SQL and two retrieved nightly rows, followed by a grounded $275 answer. The mocked route test explicitly verifies the second request contains the original question and retrieved records. The clearly named temporary fixture was removed after verification. |
| No matching records | The assistant reports no matches without inventing hotels, prices, or vacancies. | **Live model and database:** ZIP 16802, October 14–15, 2026 returned `[]`; the answer reported no matching available hotel and supplied no hotel or price. Full evidence is in [`rag-context.md`](rag-context.md). |
| Missing stay night | A multi-night total is given only when every requested night has a record; missing nights are insufficient data. | **Mocked model test:** partial nightly rows reach the answer request, whose fixture reports insufficient data. |
| Recoverable SQL proposal | A schema mistake in a read-only SELECT is sent back once for correction; the corrected query passes the same SQLite authorizer and row limit before the answer request. | **Mocked model test:** an invalid `locality` column on `saved_hotels` was corrected to a `saved_hotel_zips.locality` join, returned no matches, and reached the second answer request with an empty record set. |
| Disallowed SQL | Writes, multiple statements, comments, unapproved tables/columns, and unsafe functions are rejected; stored data stays unchanged. | **Mocked query fixtures on a temporary SQLite DB:** DELETE, access to the users table, and multi-statement SQL were rejected; the course-data table snapshot remained unchanged. The error was persisted as a timestamped `error` history message, with no assistant reply. Query execution uses a read-only connection, SQLite authorizer, progress limit, and 20-row cap. |
| Frontend request | The browser sends the user's message and optional conversation ID to the application, with no provider key. | Source check confirms `POST /api/chat` sends `{message, conversation_id?}` only. FastAPI logs confirmed the app request. The embedded browser does not expose a Network panel. |
| Live model call | One real question returns a provider-generated answer through the backend. | **Verified:** `POST /api/chat` returned 200 after restarting FastAPI with the installed SDK and updated source. The configured `gpt-6-luna` generated the SQL and then a grounded answer. The initial request exposed that the model's default reasoning budget exhausted the small SQL output cap; setting supported `reasoning.effort="none"` fixed the incomplete proposal. |
| Location no-match regression | After backend restart, a locality question generates an allowed join and reports only stored data. | **Live model and browser:** “where is glen mills” produced a validated join on `hotel_id` filtering `LOWER(z.locality)`. SQLite returned `[]`, and the answer explained the catalog has no saved location record. Conversation `6164e904a68641fba122173f1cf28a60`; full SQL and answer are in [`rag-context.md`](rag-context.md). |
| Local hotel storage | Saved API hotel, ZIP context, and simulated nights can be listed and removed through the application. | **Live API check:** the temporary RAG fixture was saved with five demo-night rows and removed after comparison. |

## Conversation and restart evidence

The live conversation ID `6164e904a68641fba122173f1cf28a60` was loaded in a fresh app page, FastAPI was restarted, and the same conversation was fetched again from SQLite with all six timestamped messages, SQL proposals, and retrieved-record payloads. A later live UI smoke exchange persisted across another page reload; the transcript now contains eight messages. The saved transcript and full direct-query comparison are in [`rag-context.md`](rag-context.md).

## Live successful example

Temporary fixture data for `Codex RAG Validation Hotel` in State College/ZIP 16802:

- October 10: $125.00, 4 rooms.
- October 11: $150.00, 2 rooms.
- Checkout October 12 is excluded. Simulated two-night total: $275.00.

The live model proposed this query, which the backend accepted and executed read-only:

```sql
SELECT
  h.hotel_id,
  h.name,
  h.address,
  z.locality,
  z.postcode,
  n.stay_date,
  n.nightly_rate_cents,
  n.rooms_available,
  SUM(n.nightly_rate_cents) OVER (PARTITION BY h.hotel_id) AS stay_total_cents
FROM saved_hotels AS h
JOIN saved_hotel_zips AS z ON z.hotel_id = h.hotel_id
JOIN demo_hotel_nights AS n ON n.hotel_id = h.hotel_id
WHERE h.name = 'Codex RAG Validation Hotel'
  AND z.locality = 'State College'
  AND n.stay_date >= '2026-10-10'
  AND n.stay_date < '2026-10-12'
ORDER BY n.stay_date
LIMIT 20;
```

Retrieved rows contained October 10 at 12,500 cents with 4 rooms and October 11 at 15,000 cents with 2 rooms; both carried the SQL-computed total of 27,500 cents. The frontend answer stated both nights, the $275 total, that checkout is excluded, and that both requested nights had records. Values were identified as simulated course data. The fixture was deleted from the local SQLite catalog after the browser check.

## Verification commands

- Focused backend checks: RAG, OpenAI configuration, and saved-hotel schema suites — 13 passed. All provider responses in automated RAG tests are labeled mock fixtures.
- Frontend checks: Oxlint and ESLint passed for the chat files; `npm run build` passed.
- Live browser smoke: verified above. The browser Network panel is not exposed in the embedded browser; FastAPI logged the app's `POST /api/chat` request, and source inspection confirms the request body is only `{message}`.
