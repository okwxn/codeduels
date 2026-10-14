importScripts('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js');
const ready = loadPyodide();
onmessage = async (e) => {
  const { code, entry, tests, checker } = e.data;
  const py = await ready;
  py.globals.set('user_code', code);
  py.globals.set('entry', entry);
  py.globals.set('tests_json', JSON.stringify(tests));
  py.globals.set('checker_src', checker || '');
  try {
    const out = await py.runPythonAsync(`
import json, sys, copy, math
ns = {}
exec(compile(user_code, '<user>', 'exec'), ns)
f = ns[entry]
chk = None
if checker_src:
    cns = {}
    exec(checker_src, cns)
    chk = cns['check']
tests = json.loads(tests_json)

def run(t):
    a = copy.deepcopy(t['args'])
    try:
        got = f(*a)
    except Exception as ex:
        return False, 'ERR: ' + repr(ex)
    try:
        if chk: ok = bool(chk(t['args'], got, t.get('expected')))
        elif t.get('unordered'): ok = sorted(got) == sorted(t['expected'])
        else: ok = got == t['expected']
    except Exception:
        ok = False
    return ok, repr(got)

passed, fail = 0, None
for t in tests:
    ok, got = run(t)
    if ok: passed += 1
    elif fail is None: fail = {'args': t['args'], 'expected': t.get('expected'), 'got': got}

steps, space, slope = 0, -1, None
if passed == len(tests):
    # 1) steps: executed lines of user code, per test
    c = [0]
    def local(fr, ev, arg):
        if ev == 'line': c[0] += 1
        return local
    def glob(fr, ev, arg):
        return local if fr.f_code.co_filename == '<user>' else None
    pts = []
    sys.settrace(glob)
    try:
        for t in tests:
            before = c[0]
            run(t)
            if t.get('n', 0) >= 20 and c[0] > before:
                pts.append((t['n'], c[0] - before))
    finally:
        sys.settrace(None)
    steps = c[0]
    # 2) growth: slope of log(steps) vs log(n)
    if len({n for n, _ in pts}) >= 3:
        xs = [math.log(n) for n, _ in pts]
        ys = [math.log(s) for _, s in pts]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        den = sum((x - mx) ** 2 for x in xs)
        if den: slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    # 3) space: peak extra bytes allocated during a call (-1 if tracemalloc unavailable)
    try:
        import tracemalloc
        peak = 0
        for t in tests:
            a = copy.deepcopy(t['args'])
            tracemalloc.start()
            try:
                base = tracemalloc.get_traced_memory()[0]
                try: f(*a)
                except Exception: pass
                peak = max(peak, tracemalloc.get_traced_memory()[1] - base)
            finally:
                tracemalloc.stop()
        space = max(0, peak)
    except Exception:
        space = -1

json.dumps({'passed': passed, 'total': len(tests), 'fail': fail, 'steps': steps, 'space': space, 'slope': slope})
`);
    postMessage(JSON.parse(out));
  } catch (err) { postMessage({ error: String(err).slice(-400) }); }
};