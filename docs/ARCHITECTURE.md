# Architecture
- Backend: FastAPI (`server/`). Rooms live in memory (`server/registry.py`), so run ONE instance and ONE uvicorn process.
- `room.py` is the match state machine (lobby -> running -> finished). `scoring.py` ranks players (pure functions). `routes.py` has the REST + WebSocket endpoints.
- Judging: public/worker.js loads Pyodide and judge/harness.py (served at /judge/harness.py) and reports steps, memory and a growth estimate. The harness is unit-tested in CPython (tests/test_harness.py). Results are client-reported (trusted).
- Problems: `problems_src/<id>/` (ref, brute, gen, check?, wrong/*) -> `tools/gen_tests.py` -> `problems/<id>.json` (committed, loaded at startup).
- WebSocket: client sends `start` and `result {idx, passed, steps, space, slope}`. Server sends `state`, `event`, and `gone`/`full`/`closed`.
- Deploy: Dockerfile -> Render (auto-deploy from `main`). Free tier sleeps, and sleep/redeploy wipes rooms.