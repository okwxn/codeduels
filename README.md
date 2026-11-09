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
Everything goes through [mise](https://mise.jdx.dev), which pins Python and uv in `.mise/config.toml`. No separate Python or uv install is needed.

1. [Install mise](https://mise.jdx.dev/getting-started.html) and [activate it in your shell](https://mise.jdx.dev/getting-started.html#activate-mise) (e.g. `eval "$(mise activate zsh)"` in `~/.zshrc`)
2. From the repo:
   ```bash
   mise trust && mise install   # trust the config, install pinned Python + uv
   cd .. && cd -                # re-enter so the hook creates/syncs .venv and installs pre-commit
   mise r gen                   # build problems/*.json from problems_src/
   mise r dev                   # http://localhost:3000
   ```

After that, entering the repo keeps `.venv` activated and synced.
Open the match link in an incognito window as the second player (same browser = same player ID).

## Development
```bash
mise tasks      # list all tasks
mise r check    # ruff lint + format check, ty type check
mise r fix      # ruff autofix + format
mise r build    # docker build (uses the Dockerfile's pinned images, not mise's)
```
Tasks live in `.mise/tasks/`. Pre-commit hooks (ruff + ty) are installed automatically when you enter the repo.

## Add problems
1. Ask Claude for problems in the format `tools/new_problem.py` expects: `=== meta.json ===`, `ref.py`, `brute.py`, `gen.py`, and optional `check.py` sections
2. Copy the reply, then run `mise r add`
3. Restart `mise r dev`, commit, push

`tools/gen_tests.py` generates the tests from `ref.py` and `gen.py`, and fails if `ref.py` and `brute.py` disagree on random inputs.

```
problems_src/<id>/   meta.json, ref.py, brute.py, gen.py, check.py?
problems/<id>.json   generated, committed, loaded by the server
tools/               gen_tests.py, new_problem.py
.mise/               tool versions + tasks
public/              index.html, worker.js
server/              FastAPI app: routes, rooms, scoring
```

## Deploy
Push to `main`. Render builds the Dockerfile and auto-deploys (set Render's auto-deploy to "After CI checks pass" so a failing build never ships).

CI builds and smoke-tests the image on every PR and push to `main`.
Base images are pinned by digest in the `Dockerfile`; when bumping Python/uv in `.mise/config.toml`, update the Dockerfile too (CI fails if they drift).

## Known limits
- Judging is client-side, so a tampered client can fake results. Fine for friends; server-side judging would fix it.
- Rooms are in memory, so a restart, sleep, or deploy ends all matches. Run a single instance and a single uvicorn process.
- Steps count executed lines of your code, so builtins like `sorted()` count as one. Memory and growth are rough estimates.
- Python only. No linked-list, tree, or design problems yet.

---
🤖 **Note:** This project was developed with the assistance of Claude Code.
