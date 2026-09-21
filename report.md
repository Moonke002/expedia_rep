# Expedia Rep — Part 2

## Repository and commit

[GitHub repository](https://github.com/Moonke002/expedia_rep). The exact Part 2 implementation commit is [`bc1b303ead15f46f70b8be0abbe544872aa89c8f`](https://github.com/Moonke002/expedia_rep/commit/bc1b303ead15f46f70b8be0abbe544872aa89c8f). The [Part 1 report](https://github.com/Moonke002/expedia_rep/blob/bbdc1eac6403093450f80eaa2347436952d9bdf6/report.md) remains available at its earlier commit.

## Implementation

Since Part 1, the Vue interface gained a clearer Expedia-inspired hero, grouped hotel search, illustrated stay cards, city and nightly-price filters, sorting, and an interactive two-month planning calendar. The calendar is explicitly a preference tool: trips retain their fixed dates.

The frontend now provides every simulated booking action. A user selects a demo traveler, creates a booking from a stay card, reads it in booking history, cancels it by updating its status while retaining the record, and deletes a UI-created test booking after an in-page confirmation. FastAPI validates these requests. The backend joins hotels and trips through `hotel_id`, reads travelers and initial bookings from CSV, and persists booking changes in a local ignored SQLite file. No payment or real inventory reservation occurs.

## Verification

- Manual code and visual review: inspected the changed source and Git diff, checked the refreshed browser screen and two-month calendar, and reviewed the repository screenshots. A VS Code-specific scan was not available in this environment.
- Search: entered `Inn`. Expected Maple Square Inn, Liberty Lane Inn, and Valley Trail Inn. Observed those three hotels across four fixed-date stays. Entered `Trail`; expected and observed Valley Trail Inn. Entered `No Such Hotel`; expected and observed the no-results message.
- Calendar: opened the date control, selected September 24–28, 2026, and closed it. Expected a visible two-month calendar and a selected planning range without changing offered stay dates; observed both.
- Create/read: clicked **Book this stay** for Valley Trail Inn as Demo Traveler 1, then reloaded and opened booking history. Expected a confirmed booking to persist; observed it in history alongside the sample bookings.
- Update/delete: clicked **Cancel booking** on the new test booking. Expected a cancelled status with the row retained; observed it. Then used **Delete test booking** and **Confirm delete**. Expected only the test row to disappear; observed the two supplied sample bookings remain. Selecting Demo Traveler 2 showed that traveler's separate sample booking.
- Automated checks: 3 backend tests passed; Oxlint, ESLint, Vite production build, and `git diff --check` passed. The backend test run emitted two dependency deprecation warnings but no failures.
- Screenshots: [search result](https://github.com/Moonke002/expedia_rep/blob/bc1b303ead15f46f70b8be0abbe544872aa89c8f/docs/screenshots/part-2-search.png) and [cancelled booking history](https://github.com/Moonke002/expedia_rep/blob/bc1b303ead15f46f70b8be0abbe544872aa89c8f/docs/screenshots/part-2-history.png).

## Project context and next steps

- [README.md](https://github.com/Moonke002/expedia_rep/blob/bc1b303ead15f46f70b8be0abbe544872aa89c8f/README.md) — setup and run instructions.
- [AGENTS.md](https://github.com/Moonke002/expedia_rep/blob/bc1b303ead15f46f70b8be0abbe544872aa89c8f/AGENTS.md) — project rules.
- [Design and UI research note](https://github.com/Moonke002/expedia_rep/blob/bc1b303ead15f46f70b8be0abbe544872aa89c8f/docs/design.md) — frontend, FastAPI, and backend responsibilities.
- [Selected Part 2 prompt](https://github.com/Moonke002/expedia_rep/blob/bc1b303ead15f46f70b8be0abbe544872aa89c8f/prompts/part-2.md) — requested scope.
- [Current handoff](https://github.com/Moonke002/expedia_rep/blob/master/handoffs/current.md) — checks and limits.

The supplied data has no real room inventory, payments, property photos, ratings, flights, taxes, or fees. The local MOV reference could not be played through the browser's local-file policy; its companion PDF describes the visual outcome and interactions. The next task is to review the Part 2 screen and diff with the instructor, then define any additional data and services needed for a real booking flow.
