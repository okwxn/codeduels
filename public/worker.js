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
import json, sys, copy
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

cost = 0
if passed == len(tests):
    c = [0]
    def local(fr, ev, arg):
        if ev == 'line': c[0] += 1
        return local
    def glob(fr, ev, arg):
        return local if fr.f_code.co_filename == '<user>' else None
    sys.settrace(glob)
    try:
        for t in tests: run(t)
    finally:
        sys.settrace(None)
    cost = c[0]
json.dumps({'passed': passed, 'total': len(tests), 'fail': fail, 'cost': cost})
`);
    postMessage(JSON.parse(out));
  } catch (err) { postMessage({ error: String(err).slice(-400) }); }
};