# Part 2 design and UI research

## Research direction

The supplied UI Research activity starts from a working `Trail` hotel search, compares Expedia, Priceline, and Booking.com, and selects an Expedia-style layout and travel illustration with a two-month calendar interaction. The supplied possible-outcome video is described in the activity PDF; direct playback of the local MOV was blocked by the browser's local-file policy. The design preserves `Trail` and `Inn` search while using a clear hero, grouped search controls, illustrated result cards, and a visible booking-history path.

## Responsibilities

- Vue owns search, city/price filters, sorting, the planning calendar, traveler selection, booking controls, feedback, and history display. Dates in the calendar are planning preferences; each offered trip keeps its supplied fixed dates.
- FastAPI validates search and booking requests and exposes `/api/hotels/search`, `/api/users`, `/api/bookings`, `/api/bookings/{booking_id}`, and `/health`.
- The backend reads hotels and trips from CSV, joined by `hotel_id`. Users and initial bookings come from the supplied CSVs. SQLite stores changes to simulated bookings so history survives reloads. Cancelling updates status; deleting is limited to UI-created test bookings.

## Data limits

No real booking, inventory reservation, payment, photo, rating, tax, fee, or flight service is connected. The stay total is nightly rate × nights. Illustrations replace absent property photos and the UI labels the transaction as a simulation.
