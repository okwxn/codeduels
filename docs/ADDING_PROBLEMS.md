# Adding problems
Problems are generated, not hand-written JSON.

    problems_src/<id>/{meta.json, ref.py, brute.py, gen.py, check.py?, wrong/*.py?}
      -> mise r gen ->  problems/<id>.json   (committed, loaded at server start)

## Files
- `meta.json`: id, title, difficulty (easy|medium|hard), tags (kebab-case), statement (own words), entry (function name), starter (stub), optional `"unordered": true` (flat lists only), optional `fixed_tests`
- `ref.py` / `brute.py`: `def solve(*args)`. ref is optimal, brute is obviously correct
- `gen.py`: `def gen(rng, size)` returns the args list, valid for any size >= 0
- `check.py`: `def check(args, got, expected)`. Decides from args alone. Required when several answers are valid or the answer is a list of lists
- `wrong/wrong_N.py`: plausible buggy solutions that must FAIL the generated tests

## Workflow
1. Add a folder under `problems_src/`, or copy an LLM reply and run `mise r add` to split it into folders.
2. `mise r gen`: checks ref against brute on random inputs, checks the wrong solutions fail, writes `problems/<id>.json`.
3. `mise r gen --check` fails if committed JSON is stale (CI runs it).
4. Commit `problems_src/` and `problems/` together.

## Generating problems with an LLM

Problems can be drafted by an LLM and split into folders by `tools/new_problem.py`. Do it in batches of about 10, because longer replies get cut off.

### Steps
1. List the ids already in the bank: `ls problems_src | paste -sd, -`
2. Send the prompt below to the LLM, with the new ids and the list from step 1.
3. Copy the WHOLE reply, then run:
   ```bash
   mise r add     # clipboard -> problems_src/<id>/ (existing ids are skipped and reported)
   mise r gen     # builds problems/*.json and runs all checks
   ```
4. Fix anything marked `FAILED` (see Troubleshooting).
5. Run `mise r dev`, play a quick match, and **read every new statement**. The checks prove that ref and brute agree, not that the wording is right.
6. Commit `problems_src/` and `problems/` together.

### Prompt
```
Create these 10 CodeDuels problems, using exactly these ids: <ids>.
(Or: Create 10 NEW problems about <topic>.)
Do not create any of these (already in the bank): <paste the ls output>

For each, output exactly these sections, each starting with a line like `=== meta.json ===`, in this order: meta.json, ref.py, brute.py, gen.py, check.py (only if several answers can be valid), then 2 wrong solutions named `=== <id>/wrong_1.py ===` and `=== <id>/wrong_2.py ===`. No other text. If you run out of space, stop cleanly after the last complete problem.
- meta.json: id, title, difficulty, tags (lowercase kebab-case, from: array, hash-map, two-pointers, sliding-window, stack, binary-search, dynamic-programming, graph, heap, intervals, greedy, backtracking, bit-manipulation, matrix, string, prefix-sum), statement in your own words with 1-2 examples, entry (function name), starter (Python stub), and "unordered": true only if the answer is a FLAT list whose order is irrelevant
- ref.py / brute.py: def solve(*args), ref is optimal, brute is obviously correct
- gen.py: def gen(rng, size) returns the args list, valid for any size >= 0 and small enough that brute force stays fast. Keep inputs within the problem's constraints, and make sure any "exactly one answer" promise in the statement is actually true for generated inputs
- check.py: def check(args, got, expected) must decide correctness from args alone. It may recompute the right answer itself, and it must ignore `expected`. Required for any answer that is a list of lists, or any problem with several valid answers
- wrong_N.py: def solve(*args), a plausible buggy attempt that passes the statement's examples but fails on some small input (up to 10 elements)
- Args and outputs must be JSON-serializable. Keep numbers under 2^53. Python only.
```

### Rules of thumb
- Ids are kebab-case and unique. The same id is skipped. A different id for the same problem creates a duplicate.
- Statements must be in your own words, never copied from LeetCode or any other site.
- Not supported yet: linked-list, tree and design problems.
- Tags drive the topic checkboxes on the create-match form. Reuse existing tags.
- Tests are visible in the browser, since judging is client-side.

### Troubleshooting
| `mise r add` / `mise r gen` output | Meaning | Fix |
|---|---|---|
| `ok <id> N tests` | good | nothing |
| `skip <id>: already exists` | id already in the bank | ignore it, or redo with `--force` |
| `problem is missing: {...}` | reply truncated, or a section header is malformed | ask the LLM to continue from the first unfinished problem, copy that reply, and run `mise r add` again |
| `FAILED <id> - ref/brute disagree…` | brute force or generator is wrong | send the LLM that error, ask for that problem's files again, then `pbpaste \| uv run python tools/new_problem.py --force && mise r gen` (`--force` wipes the folder, so include the `wrong/` sections again) |
| `FAILED <id> - wrong solution … passes ALL tests` | the buggy solution isn't actually wrong, or the tests miss that case | ask which input breaks it, add that input to `fixed_tests` in `meta.json`, or fix `gen.py` |
| `FAILED <id> - ref fails its own checker` | checker is wrong or too strict | fix `check.py` |
| "No problems match those filters" in a match | `problems/` is empty or not committed | run `mise r gen` and check `git ls-files problems` |

Other problems still generate when one fails. `mise r gen --check` fails when committed JSON is stale, and CI runs it.

### Backfilling `wrong/` solutions for older problems
1. Print ids and signatures:
   ```bash
   uv run python -c "import json,glob;[print(json.load(open(f))['id'],'|',json.load(open(f))['starter'].splitlines()[0]) for f in sorted(glob.glob('problems_src/*/meta.json'))]"
   ```
2. Send the LLM:
   ```
   Here are existing CodeDuels problems (id | function signature): <paste output>
   For each, output only 2 buggy solutions as sections named `=== <id>/wrong_1.py ===` and `=== <id>/wrong_2.py ===`. Each is `def solve(*args)` (same argument order as the signature), plausible but wrong on some small input (up to 10 elements) while passing the obvious examples. No other text.
   ```
3. Copy the reply, then run `mise r add && mise r gen`.