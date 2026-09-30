# Current handoff

## Working

- Four CSVs seed SQLite once; existing IDs and legacy booking changes survive. Hotels/trips, users, bookings, sessions, and search history are then stored in SQLite.
- Demo account creation, sign-in, session persistence, and logout work. Seeded travelers U001–U006 use `demo1`–`demo6` / `DemoPass123!`; new accounts receive unique user IDs. Booking history and changes are bound to the signed-in account.
- Signed-in hotel-name searches are recorded per user. The fourth same-query search in a UTC day raises the returned displayed rate by 20% once; the stored base rate does not change. The Vue View shows the returned rate and recalculates filters, sorting, and stay totals from it. Guests see base rates.

## Checked

- Six isolated backend tests pass, covering seed relationships, account creation/login/logout and restart, booking ownership/CRUD, query normalization, per-user pricing, noncompounding threshold, UTC rollover, unchanged base rate, SQLite-only post-seed reads, and legacy migration. Two dependency deprecation warnings remain.
- Frontend Oxlint, ESLint, and production build pass. The live database upgrade retained 8 hotels, 12 trips, 6 users, 7 bookings, and the cancelled B001; foreign-key check found no violations. In the browser, `demo1` signed in, `Trail` searches 2–3 showed $100, search 4 showed $120 and the $100 base, the signed-in history showed only U001's three records, and logout restored the guest $100 rate.
- Frontend CRUD persistence: created post-seed booking `B88480DB26DFD44DF` through **Book this stay**; it appeared in history, survived a browser refresh and a frontend/backend restart, changed to `cancelled` through **Cancel booking** and remained after refresh, then was removed through the confirmed **Delete test booking** flow and remained absent after refresh and a second frontend/backend restart. Starter bookings B001–B006 remained present once each. A fresh browser smoke pass returned Valley Trail Inn for `Trail`, showed the expected no-results message for `No Such Hotel`, signed in as `demo1`, and displayed four account-owned history records. The requested manual scan was performed at source level; the VS Code native window was not exposed to this session for a visual editor scan.

## Limitations and next task

- Demo credentials are intentionally shared; this is not production authentication or real pricing. No account recovery, payment, inventory reservation, real media, flights, taxes, or fees. The catalog has no hotel/trip editor.
- Next: review the account and pricing browser flow with the instructor, then decide whether to expand catalog management or make the authentication/pricing model production-grade.
