# RAG lookup evidence — October 8, 2026

## Live conversation

- Conversation ID: `6164e904a68641fba122173f1cf28a60`
- Provider/model: live OpenAI API call using the configured `gpt-6-luna` model.
- Data status: `RAG Context Demo Inn` was a temporary, labeled course fixture created for this check. Its simulated nightly rates and room counts were removed from the catalog after collecting the evidence below. The saved conversation retains the SQL and records returned during the check.

## Relevant schema and joins

The assistant reads only these local SQLite catalog tables:

| Table | Relevant columns | Use |
|---|---|---|
| `saved_hotels` | `hotel_id` (primary key), `name`, `address` | Saved API hotel identity and display details. |
| `saved_hotel_zips` | `hotel_id` (foreign key), `postcode`, `locality`, `country_code` | ZIP/location context for a saved hotel. |
| `demo_hotel_nights` | `hotel_id` (foreign key), `stay_date`, `nightly_rate_cents`, `rooms_available` | Dated simulated course rates and availability. |

The lookup uses both catalog relationships:

1. `saved_hotels.hotel_id = saved_hotel_zips.hotel_id` joins each saved hotel to its ZIP/location context.
2. `saved_hotels.hotel_id = demo_hotel_nights.hotel_id` joins each saved hotel to its dated demo rate and room count.

For a stay, check-in is included and checkout is excluded. The availability lookup requires a dated row with `rooms_available > 0`; a missing date is not treated as available. The database returns at most 20 rows through a read-only connection and SQLite authorizer.

## Successful lookup and direct database comparison

**Question:** “Find available saved hotel rooms in ZIP 16802 for check-in October 10, 2026 and checkout October 12, 2026. List each night price and room count, and total.”

The live model proposed this SQL. It was validated by the backend and then run against the local SQLite database. The same query was run directly against the database in read-only mode for comparison:

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

**Direct database rows and chatbot retrieval:**

| Hotel | ZIP | Stay date | Nightly rate | Rooms |
|---|---:|---|---:|---:|
| RAG Context Demo Inn | 16802 | 2026-10-10 | $125.00 | 4 |
| RAG Context Demo Inn | 16802 | 2026-10-11 | $150.00 | 2 |

**Final answer shown in the app:** RAG Context Demo Inn had returned available-room records for both requested nights: October 10 at $125 with 4 rooms and October 11 at $150 with 2 rooms. The two-night total was $275. Checkout day was excluded. The answer labeled the values simulated course data.

**Expected vs observed:** Expected exactly two nightly rows and a $275 sum; observed those same two rows in the direct SQLite query, persisted retrieval payload, and displayed answer.

## Changed-date comparison

**Question:** “For ZIP 16802, now compare check-in October 12, 2026 to checkout October 14, 2026. Show each available night, rate, rooms, and total.”

The live model generated this query with the same two joins and ZIP filter, and changed the date window to `>= '2026-10-12' AND < '2026-10-14'`:

```sql
SELECT
  h.hotel_id,
  h.name,
  h.address,
  n.stay_date,
  n.nightly_rate_cents,
  n.rooms_available,
  SUM(n.nightly_rate_cents) OVER (PARTITION BY h.hotel_id) AS total_nightly_rate_cents
FROM saved_hotels AS h
JOIN saved_hotel_zips AS z ON z.hotel_id = h.hotel_id
JOIN demo_hotel_nights AS n ON n.hotel_id = h.hotel_id
WHERE z.postcode = '16802'
  AND n.stay_date >= '2026-10-12'
  AND n.stay_date < '2026-10-14'
  AND n.rooms_available > 0
ORDER BY h.name, n.stay_date
LIMIT 20;
```

The direct database query returned:

| Hotel | ZIP | Stay date | Nightly rate | Rooms |
|---|---:|---|---:|---:|
| RAG Context Demo Inn | 16802 | 2026-10-12 | $110.00 | 8 |
| RAG Context Demo Inn | 16802 | 2026-10-13 | $120.00 | 6 |

The live answer named both dates and reported a $230 two-night total. The SQL-computed total was 23,000 cents on each row. **Expected vs observed:** changing the dates changes both the generated predicates and rows; the direct query and chatbot showed the same two new dates and rates.

## No-match lookup

**Question:** “Are any saved rooms available in ZIP 16802 for check-in October 14, 2026 and checkout October 15, 2026? If no rows match, explain that and do not suggest a specific alternative unless the database returned it.”

The generated query used the same ZIP and join conditions with `n.stay_date >= '2026-10-14'`, `n.stay_date < '2026-10-15'`, and `n.rooms_available > 0`. Direct SQLite and chatbot retrieval both returned `[]`. The answer said no saved hotel matched ZIP 16802 for the October 14 night with rooms available, and did not name a hotel or price. **Expected vs observed:** no matching rows and no invented alternatives; observed exactly that.

## Blocked write and failed-attempt history

This safety check used the labeled pytest fixture database (`tmp_path`), not the course database, and used a mock OpenAI client. The mock proposed `DELETE FROM saved_hotels`. The backend rejected the proposal before the second model request or query execution. The mock test confirms:

- The failure conversation has timestamped `user` and `error` messages, with error content recorded in `chat_messages`.
- For `DELETE FROM saved_hotels`, the stored error is `The proposed database query was not a single allowed SELECT.`
- It has no `assistant` message, so no successful reply was fabricated.
- The mock received exactly one call (the SQL proposal request); the answer-generation call did not run.
- A before/after snapshot of `hotels`, `trips`, `users`, `bookings`, `saved_hotels`, `saved_hotel_zips`, and `demo_hotel_nights` was identical.

The same test labels and rejects attempts to read `users` and to execute multiple statements. Additional checks reject unsafe SQLite functions. **Expected vs observed:** write denied and no protected row changes; observed in the isolated fixture DB. No write test was run against the course DB.

## Persistence across page load and backend restart

After the first three live exchanges, I opened a fresh app page and restarted FastAPI. The page restored the conversation using the same conversation ID, and the history endpoint returned all six messages after restart. A later live UI smoke question added a fourth user/assistant pair; after reloading again, the app displayed that answer and its SQL and row. The current history endpoint returns all eight messages. The database has four `user` and four `assistant` rows with UTC timestamps, content, proposed SQL, and retrieved-record JSON on assistant rows.

**Additional live UI smoke question:** “Find available saved hotel rooms in ZIP 16802 for check-in October 10, 2026 and checkout October 11, 2026. Tell me the hotel, nightly price, and room count.” The query returned one row for the temporary `Smoke Test Inn` fixture: October 10, 10,000 cents ($100), 20 rooms. The model answer matched those values and labeled them simulated course data. The fixture was then removed; the persisted conversation retains the result record.

The conversation remains in SQLite independently of the temporary hotel fixture. Baseline protected course-data counts were 8 hotels, 12 trips, 6 users, and 9 bookings; those counts were unchanged by the RAG checks. After cleanup, the temporary fixture was also absent from `saved_hotels`, `saved_hotel_zips`, and `demo_hotel_nights`.

## Verification summary

| Check | Expected | Observed |
|---|---|---|
| Direct query vs chatbot | Same rows for same ZIP and dates | Two matching nightly rows and the same $275 answer. |
| Change dates | Generated date filters and rows change | Oct 12–13 rows and $230 answer. |
| No match | Empty records and no invented hotel/price | Empty retrieval and explicit no-match answer. |
| Disallowed write | Reject before execution, preserve data | Mocked `DELETE` rejected; isolated DB snapshot unchanged. |
| Failure history | Persist user and error, no assistant reply | Mocked failure conversation has timestamped user/error messages only. |
| Restart and reload persistence | Reload same conversation and evidence | Same ID and six messages after backend restart; the later UI smoke exchange persisted through a further page reload, bringing the transcript to eight messages. |
| Course data | Preserve supplied hotel/user/booking records | Baseline counts remained 8/12/6/9; temporary RAG fixture removed. |

## Live regression check after backend restart — October 8, 2026

**Question:** “where is glen mills”

The first failure was caused by the backend process running an older version without source reload. The project-owned process on port 8001 was restarted with `--reload`; `/health` then reported status `ok`, that an API key was configured, and model `gpt-6-luna` without exposing the key.

**Conversation ID:** `6164e904a68641fba122173f1cf28a60`

The live model proposed this read-only locality lookup, which passed the SQLite authorizer:

```sql
SELECT DISTINCT
  z.locality,
  z.postcode,
  z.country_code,
  h.address,
  z.latitude,
  z.longitude
FROM saved_hotel_zips AS z
JOIN saved_hotels AS h ON h.hotel_id = z.hotel_id
WHERE LOWER(z.locality) = 'glen mills'
LIMIT 20;
```

SQLite returned `[]` because the current saved-hotel catalog is empty. The second model request returned: “I couldn’t find any saved hotel records matching ‘Glen Mills,’ so the catalog doesn’t provide its location.” The answer and query were visible in the popup, and the conversation reloaded from history. **Expected vs observed:** no saved locality row means no claimed location; observed an empty retrieval and a clear no-match answer. This live check verifies the flow; a Glen Mills hotel must be saved before the assistant can report its stored locality/address.
