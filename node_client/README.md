# Node Client (Integration Signal)

This folder shows Node.js interoperability with the Python FastAPI backend.

## Why This Exists

Recruiters can verify that the project supports polyglot startup workflows (Python backend + Node-based clients/services).

## Usage

```bash
cd node_client
npm install
npm run start
npm run chat
npm run reminder
```

## Environment Variables

- `SHOWCASE_API_URL` (default: `http://127.0.0.1:8001`)
- `SHOWCASE_API_TOKEN` (optional; required only if token auth is enabled in backend)

## Commands

- `npm run start` -> checks health
- `npm run chat` -> sample chat call
- `npm run reminder` -> sample reminder creation call
