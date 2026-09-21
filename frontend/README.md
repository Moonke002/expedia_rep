# Expedia Rep frontend

This Vue 3 and Vite frontend provides hotel search, an interactive planning calendar, stay cards, and simulated booking history with create, cancel, and delete controls.

## Setup

```sh
npm install
```

## Development

```sh
npm run dev
```

## Checks

```sh
.\node_modules\.bin\oxlint.cmd .
.\node_modules\.bin\eslint.cmd .
npm run build
```

The screen uses illustrated placeholders because the CSVs contain no photos. The planning calendar does not filter fixed-date offers; booking actions call the local FastAPI backend and do not charge or reserve inventory.
