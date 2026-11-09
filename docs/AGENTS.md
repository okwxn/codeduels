# Working in this repo
- Setup: `mise install && uv sync`. Run: `mise r dev`. Before pushing: `mise r fix && mise r check && mise r test`.
- Problems: edit `problems_src/`, run `mise r gen`, commit the generated `problems/*.json`. Never hand-edit `problems/`.
- Keep modules small and typed. Game rules belong in `server/room.py` / `server/scoring.py`, and every rule change needs a test in `tests/`.
- No accounts, and nothing per-user on the server beyond the in-memory room.
- `main` auto-deploys to production. Work in branches and open a PR.