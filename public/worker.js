importScripts('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js');
const ready = loadPyodide();
onmessage = async (e) => {
  const { code, entry, tests } = e.data;
  const py = await ready;
  py.globals.set('user_code', code);
  py.globals.set('entry', entry);
  py.globals.set('tests_json', JSON.stringify(tests));
  try {
    const out = await py.runPythonAsync(`
import json
ns = {}
exec(user_code, ns)
f = ns[entry]
passed, fail = 0, None
tests = json.loads(tests_json)
for t in tests:
    try:
        got = f(*t['args'])
    except Exception as ex:
        got = 'ERR: ' + repr(ex)
    try:
        ok = sorted(got) == sorted(t['expected']) if t.get('unordered') else got == t['expected']
    except Exception:
        ok = False
    if ok: passed += 1
    elif fail is None: fail = {'args': t['args'], 'expected': t['expected'], 'got': repr(got)}
json.dumps({'passed': passed, 'total': len(tests), 'fail': fail})
`);
    postMessage(JSON.parse(out));
  } catch (err) { postMessage({ error: String(err).slice(-400) }); }
};