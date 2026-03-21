# Frontend

This directory contains a lightweight single-page frontend for the Vectorless System Design Assistant.

Features
- Simple SPA (no build tools required)
- Ask queries to the backend `/query` endpoint
- View answer, traversal path and confidence
- Query history and debug view

Run locally (development)
1. Ensure the backend is running: `python backend/src/main.py` (server listens on `http://localhost:8000`)
2. Serve the `frontend` directory (static) so the browser can load assets. Easiest option:

```bash
# from repository root
python -m http.server --directory frontend 8001
# then open http://localhost:8001 in your browser
```

Notes
- The backend includes CORS support; if you host the frontend on a different port, requests should still work.
- For production, consider serving the static files from your web server or from the backend's static file handler.

