# CodeDuels

No-signup, lichess-style coding matches. Create a match, share the link, and race friends on algorithm problems. Solutions run in the browser (Python via Pyodide).

**Live:** https://codeduels.onrender.com (free tier, so the first load after idle takes ~30-60s)

## Features
- No accounts: players get a random ID and a name, stored in localStorage
- 2-6 players per match, with an invite link
- Filter by difficulty and topic, with 1-5 problems per match
- Ranking modes: fastest solve, most tests passed, fewest steps, lowest memory
- End modes: first finisher, 2 min grace window, or until the timer
- Final standings with steps, memory, a rough growth estimate, and a match timeline

## Stack
FastAPI + WebSockets (in-memory rooms), one static HTML page, Monaco editor, Pyodide in a Web Worker, Docker on Render.

## Run locally
```bash
mise install && uv sync
mise r gen      # build problems/*.json from problems_src/
mise r dev      # http://localhost:3000
```
Open the match link in an incognito window as the second player (same browser = same player ID).

## Add problems
1. Ask Claude for problems in the format `tools/new_problem.py` expects: `=== meta.json ===`, `ref.py`, `brute.py`, `gen.py`, and optional `check.py` sections
2. Copy the reply, then run `mise r add`
3. Restart `mise r dev`, commit, push

`tools/gen_tests.py` generates the tests from `ref.py` and `gen.py`, and fails if `ref.py` and `brute.py` disagree on random inputs.

```
problems_src/<id>/   meta.json, ref.py, brute.py, gen.py, check.py?
problems/<id>.json   generated, committed, loaded by the server
tools/               gen_tests.py, new_problem.py
public/              index.html, worker.js
main.py              server, rooms, scoring
```

## Deploy
Push to `main`. Render builds the Dockerfile and auto-deploys.

## Known limits
- Judging is client-side, so a tampered client can fake results. Fine for friends; server-side judging would fix it.
- Rooms are in memory, so a restart, sleep, or deploy ends all matches. Run a single instance and a single uvicorn process.
- Steps count executed lines of your code, so builtins like `sorted()` count as one. Memory and growth are rough estimates.
- Python only. No linked-list, tree, or design problems yet.

---
🤖 **Note:** This project was developed with the assistance of Claude Code.
