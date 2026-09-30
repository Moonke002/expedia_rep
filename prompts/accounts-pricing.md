# Accounts and personalized pricing request

Add functional demo account creation, sign-in, and logout while retaining seeded user IDs and booking references. Save search history per signed-in user, query, and timestamp. For the same normalized hotel-name query on a UTC day, show the base price for searches 1–3 and one 20% increase from search 4 onward; do not change the stored base rate. Keep account and booking actions through Vue, FastAPI, and Python controllers. Verify wrong credentials, duplicate usernames, logout, persistence, user separation, and day rollover.
